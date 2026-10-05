# ============================================================================
# engine/paint_v2/fable_collection.py
# FABLE — 20 fully-procedural flagship monolithics, authored 2026-06-09 with
# the engine/color_science toolkit (the "new logic" drop):
#   * OKLab/OKLCH perceptual ramps (no muddy HSV midpoints)
#   * Beer–Lambert absorption candy (real depth pooling)
#   * Quantized thin-film interference (real banded iridescence)
#   * Perceptual color-flip lattices (angle-reactive hue under iRacing light)
#   * Hue-travel roughness corridors (the highlight migrates across hues)
#   * tri_partition decorrelation-by-construction for M/R/Cc
#
# ZERO image plates: renders for every buyer with no downloads.
# UV-orientation-agnostic by design (scattered / radial / multi-angle motifs).
#
# CONTRACT (engine/registry.py):
#   MONOLITHIC_REGISTRY[id] = (spec_fn, paint_fn)
#   paint_fn(paint, shape, mask, seed, pm, bb) -> float32 HxWx3/4 in [0,1]
#   spec_fn(shape, mask, seed, sm)            -> uint8  HxWx4 (M,R,Cc,A)
# Floors: R>=15, Cc>=16. Outside-mask: M~4, R~120, Cc~80 (house convention).
#
# 2-copy file (root is source of truth; mirrored to electron-app/server via
# scripts/sync-runtime-copies.js -- listed in runtime-sync-manifest.json).
# ============================================================================
from __future__ import annotations

import hashlib
from functools import lru_cache

import cv2
import numpy as np

from engine.core import multi_scale_noise
from engine.color_science import (
    oklch_ramp,
    candy_absorb,
    interference_palette,
    tri_partition,
    flip_lattice,
    srgb_to_linear,
    linear_to_srgb,
    srgb_to_oklab,
    oklab_to_oklch,
    oklch_to_oklab,
    oklab_to_linear,
)

# ---------------------------------------------------------------------------
# SHARED PLUMBING (same proven block as cultural_let_freedom_ring; helpers do
# plumbing + spec packing only — every finish owns its primary geometry).
# ---------------------------------------------------------------------------
_WORK_CAP = 1024  # engine work-grid cap; compute small, upscale to canvas.


def _shape2(shape):
    return shape[:2] if len(shape) > 2 else shape


def _seed_of(finish_id, seed):
    base = int.from_bytes(hashlib.blake2s(finish_id.encode("utf-8"), digest_size=4).digest(), "big")
    return (base ^ (int(seed) & 0x7FFFFFFF)) & 0x7FFFFFFF


def _work_shape(shape):
    h, w = _shape2(shape)
    m = max(h, w)
    if m <= _WORK_CAP:
        return int(h), int(w), 1.0
    s = _WORK_CAP / float(m)
    return max(64, int(round(h * s))), max(64, int(round(w * s))), s


def _mask2(mask, h, w):
    if mask is None:
        return np.ones((h, w), np.float32)
    if np.isscalar(mask) or (hasattr(mask, "ndim") and getattr(mask, "ndim", 1) == 0):
        return np.full((h, w), float(mask), np.float32)
    a = np.asarray(mask, np.float32)
    if a.ndim == 3:
        a = a[:, :, 0]
    if a.shape != (h, w):
        a = cv2.resize(a, (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(a, 0.0, 1.0).astype(np.float32)


def _msc(h, w, scales, seed):
    """multi_scale_noise normalised to 0..1."""
    wts = [0.5, 0.3, 0.2][: len(scales)]
    n = multi_scale_noise((h, w), list(scales), wts, int(seed) & 0x7FFFFFFF)
    return ((np.asarray(n, np.float32) + 1.0) * 0.5).astype(np.float32)


@lru_cache(maxsize=8)
def _coords(h, w):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yn = yy / max(h - 1, 1)
    xn = xx / max(w - 1, 1)
    return yy, xx, yn, xn


def _edge(field, gain=6.0):
    dx = np.abs(np.diff(field, axis=1, prepend=field[:, :1]))
    dy = np.abs(np.diff(field, axis=0, prepend=field[:1, :]))
    return np.clip(np.sqrt(dx * dx + dy * dy) * gain, 0.0, 1.0).astype(np.float32)


def _scatter_field(h, w, seed, count, value_fn):
    """Seeded omnidirectional point scatter -> accumulation via
    value_fn(acc, yy, xx, cy, cx, rad, ang, amp)."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    acc = np.zeros((h, w), np.float32)
    yy, xx, _, _ = _coords(h, w)
    for _ in range(count):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        rad = rng.uniform(0.010, 0.034) * max(h, w)
        ang = rng.uniform(0.0, 2.0 * np.pi)
        amp = rng.uniform(0.55, 1.0)
        value_fn(acc, yy, xx, cy, cx, rad, ang, amp)
    return acc


def _upscale(arr, h, w):
    if arr.shape[:2] == (h, w):
        return arr
    return cv2.resize(arr, (w, h), interpolation=cv2.INTER_LINEAR)


# ---------------------------------------------------------------------------
# SHARED-FIELDS MEMO (SPB-PERF 2026-06-13)
# By the Wovenlight ignition doctrine, a fable finish's spec TRACES the paint's
# exact geometry: _spec_fable_<x> and _paint_fable_<x> both call the SAME field
# builder with the SAME (h, w, seed), so an expensive (0.8-2.6s) field build ran
# TWICE per render. Every such builder returns a tuple of arrays that BOTH
# callers only READ (they construct brand-new arrays from them — no in-place
# mutation of the returned arrays; verified per-builder 2026-06-13), so replaying
# a cached result is BIT-IDENTICAL. The wovenlight/magnetite/quicksilver builders
# already hand-roll this exact FIFO cache; @_memo_fields generalises it so the
# other expensive shared builders skip their redundant second build. FIFO-capped
# (3 keys: typically the live preview/booth share one (h,w,seed); the cap keeps
# memory bounded yet survives a paint->spec pair). Cheap builders are left
# un-memoized (the wrapper overhead isn't worth it below ~0.9s).
# ---------------------------------------------------------------------------
def _memo_fields(fn):
    cache = {}

    def wrapped(h, w, seed):
        key = (int(h), int(w), int(seed))
        hit = cache.get(key)
        if hit is not None:
            return hit
        out = fn(h, w, seed)
        cache[key] = out
        if len(cache) > 3:
            cache.pop(next(iter(cache)))
        return out

    wrapped.__name__ = getattr(fn, "__name__", "fields")
    wrapped.__qualname__ = getattr(fn, "__qualname__", wrapped.__name__)
    wrapped.__doc__ = fn.__doc__
    wrapped._memo_cache = cache
    wrapped.__wrapped__ = fn
    return wrapped


# ---------------------------------------------------------------------------
# _opt_* PERFORMANCE HELPERS (2026-06-09 render-speed pass; owner doctrine:
# every paint_fn/spec_fn ~1s at real size).  Same math, same rng draw order
# and count — only WHERE the work happens changes: scatter motifs evaluate in
# local windows (only sub-tolerance gaussian tails are truncated), Voronoi
# loops re-evaluate the ORIGINAL float32 metric on cKDTree candidate sets
# (bit-identical d1/d2/idx), and OKLCH ramps sample a 1-D LUT (the ramp is a
# pure function of t; interp error ~1e-4 vs the 0.02 identity tolerance).
# ---------------------------------------------------------------------------


def _opt_win(h, w, cy, cx, ry, rx=None):
    """Clipped integer window bounds around (cy, cx) with half-extent ry/rx."""
    if rx is None:
        rx = ry
    y0 = max(int(cy - ry) - 1, 0)
    y1 = min(int(cy + ry) + 2, h)
    x0 = max(int(cx - rx) - 1, 0)
    x1 = min(int(cx + rx) + 2, w)
    return y0, y1, x0, x1


def _opt_rect_win(h, w, cy, cx, ca, sa, ulo, uhi, vmax):
    """Clipped bbox of the rotated rect u in [ulo, uhi], |v| <= vmax around
    (cy, cx), where u = dx*ca + dy*sa and v = dy*ca - dx*sa."""
    xs = []
    ys = []
    for uu in (ulo, uhi):
        for vv in (-vmax, vmax):
            xs.append(uu * ca - vv * sa)
            ys.append(uu * sa + vv * ca)
    y0 = max(int(cy + min(ys)) - 1, 0)
    y1 = min(int(cy + max(ys)) + 2, h)
    x0 = max(int(cx + min(xs)) - 1, 0)
    x1 = min(int(cx + max(xs)) + 2, w)
    return y0, y1, x0, x1


def _opt_arc_bbox(h, w, cy, cx, r_lo, r_hi, ang, half_span):
    """Clipped bbox of an annular arc segment: radius in [r_lo, r_hi], angle
    within +/- half_span of ang (radians), centered on (cy, cx)."""
    if half_span >= np.pi - 1e-6:
        cmin = smin = -1.0
        cmax = smax = 1.0
    else:
        a0 = float(ang - half_span)
        a1 = float(ang + half_span)
        cands = [a0, a1]
        k = float(np.ceil(a0 / (0.5 * np.pi)))
        while k * 0.5 * np.pi <= a1 + 1e-9:
            cands.append(k * 0.5 * np.pi)
            k += 1.0
        cosv = [float(np.cos(a)) for a in cands]
        sinv = [float(np.sin(a)) for a in cands]
        cmin, cmax = min(cosv), max(cosv)
        smin, smax = min(sinv), max(sinv)
    xs = [r * c for r in (r_lo, r_hi) for c in (cmin, cmax)]
    ys = [r * s for r in (r_lo, r_hi) for s in (smin, smax)]
    y0 = max(int(cy + min(ys)) - 1, 0)
    y1 = min(int(cy + max(ys)) + 2, h)
    x0 = max(int(cx + min(xs)) - 1, 0)
    x1 = min(int(cx + max(xs)) + 2, w)
    return y0, y1, x0, x1


def _opt_scatter_field(h, w, seed, count, value_fn, win_of):
    """_scatter_field twin: identical rng draw order/count, but each splat is
    evaluated only inside its local window (win_of(rad) -> half-extent px)."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    acc = np.zeros((h, w), np.float32)
    yy, xx, _, _ = _coords(h, w)
    for _ in range(count):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        rad = rng.uniform(0.010, 0.034) * max(h, w)
        ang = rng.uniform(0.0, 2.0 * np.pi)
        amp = rng.uniform(0.55, 1.0)
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, float(win_of(rad)))
        value_fn(acc[y0:y1, x0:x1], yy[y0:y1, x0:x1], xx[y0:y1, x0:x1],
                 cy, cx, rad, ang, amp)
    return acc


def _opt_voro_top2(yq, xq, py, px, k=6, metric=None):
    """Exact drop-in for the per-site full-grid Voronoi loops -> (d1, d2, idx).

    A cKDTree proposes the k Euclidean-nearest candidate sites per pixel, then
    the ORIGINAL per-site metric is re-evaluated on just those candidates with
    the same elementwise float ops, so d1/d2/idx match the naive running-min
    loops bit-for-bit (ties resolve to the lowest site index, same as the
    strict-`<` loops).  metric(dy, dx, cand) -> dd; default squared Euclidean.
    """
    from scipy.spatial import cKDTree
    h, w = yq.shape
    n = int(len(py))
    k = int(min(k, n))
    tree = cKDTree(np.stack([np.asarray(py, np.float64),
                             np.asarray(px, np.float64)], axis=1))
    rdt = np.result_type(yq.dtype, np.asarray(py).dtype)
    d1 = np.empty((h, w), rdt)
    d2 = np.empty((h, w), rdt)
    idx = np.empty((h, w), np.int32)
    step = max(16, int((4 << 20) // max(w * k, 1)))
    big = np.int32(1 << 30)
    for y0 in range(0, h, step):
        y1 = min(y0 + step, h)
        yb = yq[y0:y1]
        xb = xq[y0:y1]
        _, cand = tree.query(np.stack([yb.ravel(), xb.ravel()], axis=1),
                             k=k, workers=-1)
        cand = cand.astype(np.int32).reshape(y1 - y0, w, k)
        dy = yb[:, :, None] - py[cand]
        dx = xb[:, :, None] - px[cand]
        dd = (dy * dy + dx * dx) if metric is None else metric(dy, dx, cand)
        two = np.partition(dd, 1, axis=2)[:, :, :2]
        d1[y0:y1] = two[:, :, 0]
        d2[y0:y1] = two[:, :, 1]
        idx[y0:y1] = np.where(dd <= two[:, :, :1], cand, big).min(axis=2)
    return d1, d2, idx


@lru_cache(maxsize=64)
def _opt_ramp_lut(stops_key, flatten, n=4096):
    """1-D LUT of oklch_ramp(t) sampled at n+1 points."""
    ts = np.linspace(0.0, 1.0, n + 1).astype(np.float32)
    return oklch_ramp([list(s) for s in stops_key], ts, flatten_lightness=flatten)


@lru_cache(maxsize=64)
def _opt_ramp_jump_cells(stops_key, flatten, n=4096):
    """Bool per LUT cell: True where the exact ramp is NOT well represented
    by linear interp inside the cell — large node-to-node delta OR a midpoint
    that deviates from the interpolated midpoint (catches the sub-cell
    staircase spikes the gamut-clamp bisection makes near-zero channels).
    Those cells get exact re-evaluation when the ramp feeds candy_absorb,
    because Beer-Lambert log-amplifies tiny tint errors."""
    lut = _opt_ramp_lut(stops_key, flatten, n)
    delta = np.abs(np.diff(lut, axis=0)).max(axis=1)
    stops = [list(s) for s in stops_key]
    mids = (np.arange(n, dtype=np.float32) + np.float32(0.5)) / np.float32(n)
    exact_mid = oklch_ramp(stops, mids, flatten_lightness=flatten)
    interp_mid = (lut[:-1] + lut[1:]) * 0.5
    mid_err = np.abs(exact_mid - interp_mid).max(axis=1)
    flags = (delta > 8e-4) | (mid_err > 2e-4)
    # Staircase-breakpoint detection: the exact ramp is smooth inside a cell
    # only if the gamut bisection's quantized chroma scale lo(t) is constant
    # across it — otherwise the true color can notch ANYWHERE inside the cell
    # (no sub-sampling can see it).  Probe lo at 5 samples per cell.
    S = 5
    stops_a = np.asarray(stops, np.float32).reshape(-1, 3)
    lch = oklab_to_oklch(srgb_to_oklab(stops_a))
    if flatten > 0.0:
        meanL = float(lch[:, 0].mean())
        lch[:, 0] = lch[:, 0] * (1.0 - flatten) + meanL * flatten
    H = lch[:, 2].copy()
    for i in range(1, len(H)):
        d = H[i] - H[i - 1]
        d = (d + np.pi) % (2.0 * np.pi) - np.pi
        H[i] = H[i - 1] + d
    tt = np.arange(n * S + 1, dtype=np.float32) / np.float32(n * S)
    n_seg = stops_a.shape[0] - 1
    x = tt * n_seg
    i0 = np.clip(np.floor(x).astype(np.int32), 0, n_seg - 1)
    f = (x - i0).astype(np.float32)
    L = lch[i0, 0] + (lch[i0 + 1, 0] - lch[i0, 0]) * f
    C = lch[i0, 1] + (lch[i0 + 1, 1] - lch[i0, 1]) * f
    Hh = H[i0] + (H[i0 + 1] - H[i0]) * f
    a = C * np.cos(Hh)
    b = C * np.sin(Hh)
    r, g, b2 = _opt_lab_to_lin_planes(L, a, b)
    bad = ((r < -1e-4) | (r > 1.0 + 1e-4) | (g < -1e-4) | (g > 1.0 + 1e-4)
           | (b2 < -1e-4) | (b2 > 1.0 + 1e-4))
    lo = np.zeros(tt.shape[0], np.float32)
    hi = np.ones(tt.shape[0], np.float32)
    for _ in range(10):
        mid = (lo + hi) * 0.5
        tr, tg, tb = _opt_lab_to_lin_planes(L, a * mid, b * mid)
        ok = ~((tr < -1e-4) | (tr > 1.0 + 1e-4) | (tg < -1e-4)
               | (tg > 1.0 + 1e-4) | (tb < -1e-4) | (tb > 1.0 + 1e-4))
        lo = np.where(ok, mid, lo)
        hi = np.where(~ok, mid, hi)
    code = np.where(bad, lo, np.float32(2.0))          # 2.0 = unclamped marker
    base = code[0:n * S:S]
    var = np.zeros(n, bool)
    for k in range(1, S + 1):
        var |= code[k::S][:n] != base
    return flags | var


def _opt_oklch_ramp(stops, t, flatten_lightness=0.0, exact_edges=False):
    """LUT-evaluated oklch_ramp: visually identical (max err ~1e-4) but skips
    the full-grid OKLab/gamut-clamp search (~1.4s/call at 1024^2 -> ~30ms).
    exact_edges=True re-runs the real oklch_ramp on the few pixels whose t
    falls in a jump cell (use for ramps that feed candy_absorb as TINT)."""
    key = tuple(tuple(float(c) for c in s) for s in stops)
    lut = _opt_ramp_lut(key, float(flatten_lightness))
    n = lut.shape[0] - 1
    ta = np.asarray(t, np.float32)
    x = np.clip(ta, 0.0, 1.0) * np.float32(n)
    i0 = np.minimum(x.astype(np.int32), n - 1)
    f = (x - i0.astype(np.float32))[..., None]
    out = (lut[i0] * (1.0 - f) + lut[i0 + 1] * f).astype(np.float32)
    if exact_edges:
        sel = _opt_ramp_jump_cells(key, float(flatten_lightness))[i0]
        if sel.any():
            out[sel] = _opt_oklch_ramp_exact(stops, ta[sel],
                                             flatten_lightness=flatten_lightness)
    return out


def _opt_lab_to_lin_planes(L, a, b):
    """Inlined oklab_to_linear on contiguous planes — verbatim constants and
    op order, so results are bit-identical (ufuncs are layout-invariant)."""
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b2 = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return r, g, b2


def _opt_linear_to_srgb(c):
    """Bitwise-identical to color_science.linear_to_srgb, but np.power runs
    only on the bright branch (the dark branch's pow result is discarded by
    the np.where anyway)."""
    c = np.clip(np.asarray(c, np.float32), 0.0, 1.0)
    out = c * 12.92
    sel = ~(c <= 0.0031308)
    if sel.any():
        out[sel] = 1.055 * np.power(c[sel], 1.0 / 2.4) - 0.055
    return out.astype(np.float32)


def _opt_gamut_bisect(Ls, As, Bs):
    """The 10-step chroma bisection of _gamut_clamp_linear on plane arrays,
    with preallocated buffers / in-place ufuncs.  Identical op order and
    operands per element -> bit-identical lo."""
    M = Ls.shape[0]
    lo = np.zeros(M, np.float32)
    hi = np.ones(M, np.float32)
    mid = np.empty(M, np.float32)
    am = np.empty(M, np.float32)
    bm = np.empty(M, np.float32)
    t1 = np.empty(M, np.float32)
    t2 = np.empty(M, np.float32)
    pl = np.empty(M, np.float32)
    pm_ = np.empty(M, np.float32)
    ps = np.empty(M, np.float32)
    racc = np.empty(M, np.float32)
    bad = np.empty(M, bool)
    tmpb = np.empty(M, bool)
    for _ in range(10):
        np.add(lo, hi, out=mid)
        np.multiply(mid, 0.5, out=mid)
        np.multiply(As, mid, out=am)
        np.multiply(Bs, mid, out=bm)
        # l_/m_/s_ cubes (same (L + c1*a) + c2*b op order as the library)
        np.multiply(am, 0.3963377774, out=t1)
        np.add(Ls, t1, out=t1)
        np.multiply(bm, 0.2158037573, out=t2)
        np.add(t1, t2, out=t1)
        np.power(t1, 3, out=pl)
        np.multiply(am, 0.1055613458, out=t1)
        np.subtract(Ls, t1, out=t1)
        np.multiply(bm, 0.0638541728, out=t2)
        np.subtract(t1, t2, out=t1)
        np.power(t1, 3, out=pm_)
        np.multiply(am, 0.0894841775, out=t1)
        np.subtract(Ls, t1, out=t1)
        np.multiply(bm, 1.2914855480, out=t2)
        np.subtract(t1, t2, out=t1)
        np.power(t1, 3, out=ps)
        # r/g/b2 channels: ((c1*l) -/+ (c2*m)) +/- (c3*s), test bounds
        np.multiply(pl, 4.0767416621, out=t1)
        np.multiply(pm_, 3.3077115913, out=t2)
        np.subtract(t1, t2, out=t1)
        np.multiply(ps, 0.2309699292, out=t2)
        np.add(t1, t2, out=racc)
        np.less(racc, -1e-4, out=bad)
        np.greater(racc, 1.0 + 1e-4, out=tmpb)
        np.logical_or(bad, tmpb, out=bad)
        np.multiply(pl, -1.2684380046, out=t1)
        np.multiply(pm_, 2.6097574011, out=t2)
        np.add(t1, t2, out=t1)
        np.multiply(ps, 0.3413193965, out=t2)
        np.subtract(t1, t2, out=racc)
        np.less(racc, -1e-4, out=tmpb)
        np.logical_or(bad, tmpb, out=bad)
        np.greater(racc, 1.0 + 1e-4, out=tmpb)
        np.logical_or(bad, tmpb, out=bad)
        np.multiply(pl, -0.0041960863, out=t1)
        np.multiply(pm_, 0.7034186147, out=t2)
        np.subtract(t1, t2, out=t1)
        np.multiply(ps, 1.7076147010, out=t2)
        np.add(t1, t2, out=racc)
        np.less(racc, -1e-4, out=tmpb)
        np.logical_or(bad, tmpb, out=bad)
        np.greater(racc, 1.0 + 1e-4, out=tmpb)
        np.logical_or(bad, tmpb, out=bad)
        # bad == ~ok: ok -> lo = mid, ~ok -> hi = mid
        np.copyto(hi, mid, where=bad)
        np.logical_not(bad, out=tmpb)
        np.copyto(lo, mid, where=tmpb)
    return lo


def _opt_oklch_ramp_exact(stops_srgb, t, flatten_lightness=0.0):
    """BIT-IDENTICAL re-implementation of color_science.oklch_ramp (hue_dir=
    'short') that runs the gamut-clamp bisection only on the out-of-gamut
    pixel SUBSET with contiguous-plane math instead of 10 full-grid strided
    iterations (~10s -> ~0.5s at 1024^2 when the clamp engages).  Use for
    ramps that feed candy_absorb as TINT with near-zero channels, where any
    LUT interp error would be log-amplified by Beer-Lambert."""
    stops = np.asarray(stops_srgb, np.float32).reshape(-1, 3)
    lch = oklab_to_oklch(srgb_to_oklab(stops))
    if flatten_lightness > 0.0:
        meanL = float(lch[:, 0].mean())
        lch[:, 0] = lch[:, 0] * (1.0 - flatten_lightness) + meanL * flatten_lightness
    H = lch[:, 2].copy()
    for i in range(1, len(H)):
        d = H[i] - H[i - 1]
        d = (d + np.pi) % (2.0 * np.pi) - np.pi
        H[i] = H[i - 1] + d
    t = np.clip(np.asarray(t, np.float32), 0.0, 1.0)
    n_seg = stops.shape[0] - 1
    x = t * n_seg
    i0 = np.clip(np.floor(x).astype(np.int32), 0, n_seg - 1)
    f = (x - i0).astype(np.float32)
    i1 = i0 + 1
    cl = [np.ascontiguousarray(lch[:, j]) for j in range(2)]
    L = np.take(cl[0], i0)
    L += (np.take(cl[0], i1) - L) * f
    C = np.take(cl[1], i0)
    C += (np.take(cl[1], i1) - C) * f
    Hh = np.take(H, i0)
    Hh += (np.take(H, i1) - Hh) * f
    a = C * np.cos(Hh)
    b = C * np.sin(Hh)
    r, g, b2 = _opt_lab_to_lin_planes(L, a, b)
    bad = ((r < -1e-4) | (r > 1.0 + 1e-4) | (g < -1e-4) | (g > 1.0 + 1e-4)
           | (b2 < -1e-4) | (b2 > 1.0 + 1e-4))
    if bad.any():
        # bisection on the bad subset only (per-pixel independent => exact)
        Ls = np.ascontiguousarray(L[bad])
        As = np.ascontiguousarray(a[bad])
        Bs = np.ascontiguousarray(b[bad])
        lo = _opt_gamut_bisect(Ls, As, Bs)
        rs, gs, bs = _opt_lab_to_lin_planes(Ls, As * lo, Bs * lo)
        r[bad] = rs
        g[bad] = gs
        b2[bad] = bs
    out = np.empty(t.shape + (3,), np.float32)
    out[..., 0] = r
    out[..., 1] = g
    out[..., 2] = b2
    return _opt_linear_to_srgb(np.clip(out, 0.0, 1.0))


def _pack_spec(M, R, Cc, mask_full, sm, h, w):
    """Assemble + clamp + apply sm + outside-mask convention. Inputs full-res HxW 0..255."""
    outside = 1.0 - mask_full
    out = np.empty((h, w, 4), np.float32)
    out[:, :, 0] = np.clip(np.clip(M, 0, 255) * float(sm) * mask_full + 4.0 * outside, 0, 255)
    out[:, :, 1] = np.clip(np.clip(R, 15, 255) * mask_full + 120.0 * outside, 15, 255)
    out[:, :, 2] = np.clip(np.clip(Cc, 16, 255) * mask_full + 80.0 * outside, 16, 255)
    out[:, :, 3] = 255
    return out.astype(np.uint8)


def _blend_paint(paint, effect, mask_full, pm):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    m3 = mask_full[:, :, None]
    s = np.clip(float(pm) * 0.98, 0.0, 1.0)
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - m3 * s) + effect[:, :, :3] * (m3 * s)
    return np.clip(paint, 0.0, 1.0).astype(np.float32)


# === FABLE FINISH BLOCKS ARE APPENDED BELOW (one block per finish) ==========


# ============================================================================
# FABLE — EMBER GLASS (fable_ember_glass)
# Blood-orange→crimson Beer–Lambert candy over coarse silver flake. A noise-
# warped Voronoi crackle is the RELIEF: the coat runs thin and fiery on the
# plateau tops and POOLS deep crimson-black inside the crack valleys (the
# relief field literally drives candy_absorb depth — real candy pooling).
# Spec decorrelation: M = its own flake-glint scatter (+ sparse gated crack-rim
# sparks <25%), R = its own 4-axis brushed micro grain, Cc = the crack-valley
# glow web with its own pooling macro.
# UV-agnostic: scattered Voronoi sites, noise-warped web, 4 random brushing
# axes — no global gradient, no centered emblem.
# ============================================================================
FAB_1 = "fable_ember_glass"


def _ember_glass_voro(h, w, seed, count):
    """Euclidean Voronoi (F1, F2) on noise-warped coords -> organic crackle."""
    mx = float(max(h, w))
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    wy = (_msc(h, w, [max(3, int(mx * 0.05)), max(5, int(mx * 0.14))], seed ^ 0x1A2B) - 0.5) * mx * 0.045
    wx = (_msc(h, w, [max(3, int(mx * 0.05)), max(5, int(mx * 0.14))], seed ^ 0x3C4D) - 0.5) * mx * 0.045
    yw = yy + wy
    xw = xx + wx
    py = rng.uniform(0, h, count).astype(np.float32)
    px = rng.uniform(0, w, count).astype(np.float32)
    d1, d2, _ = _opt_voro_top2(yw, xw, py, px)  # bit-identical to the old loop
    return np.sqrt(d1), np.sqrt(d2)


def _ember_glass_fields(h, w, seed):
    """-> (crack web, candy depth, coarse flake, macro drift), all float32 HxW."""
    mx = float(max(h, w))
    d1, d2 = _ember_glass_voro(h, w, seed ^ 0x0E1B, 110)
    gap = (d2 - d1) / mx
    crack = np.exp(-gap / 0.008).astype(np.float32)          # ~8 px work = 16 px canvas web
    rng_f = np.random.default_rng((seed ^ 0xF1AE) & 0x7FFFFFFF)
    fl = rng_f.random((h, w)).astype(np.float32)
    fl = cv2.GaussianBlur(fl, (0, 0), 0.7)
    flake = np.clip((fl - 0.62) / 0.38, 0.0, 1.0) ** 1.6     # coarse bright flake tips
    macro = _msc(h, w, [max(9, int(mx * 0.11)), max(15, int(mx * 0.3))], seed ^ 0x77AA)
    plat = _msc(h, w, [max(3, int(mx * 0.02)), max(7, int(mx * 0.06))], seed ^ 0x55EE)
    depth = np.clip(0.34 + crack * 2.3 + (macro - 0.5) * 0.5 + (plat - 0.5) * 0.18, 0.05, 3.2)
    return crack, depth.astype(np.float32), flake.astype(np.float32), macro


def _spec_fable_ember_glass(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_1, seed)
    mx = float(max(h, w))
    crack, _depth, _flake, _macro = _ember_glass_fields(h, w, s)

    # M — its own flake-glint scatter + sparse, noise-gated crack-rim sparks
    rngm = np.random.default_rng((s ^ 0x4D11) & 0x7FFFFFFF)
    g = cv2.GaussianBlur(rngm.random((h, w)).astype(np.float32), (0, 0), 0.6)
    glint = np.clip((g - 0.74) / 0.26, 0.0, 1.0) ** 2.0
    patch_m = _msc(h, w, [max(13, int(mx * 0.16)), max(21, int(mx * 0.4))], s ^ 0x4D22)
    rim = _edge(crack, gain=5.0)
    sparkgate = (rngm.random((h, w)) > 0.55).astype(np.float32)
    M = 30.0 + glint * 200.0 + patch_m * 45.0 + rim * sparkgate * 55.0

    # R — 4 random-axis brushed micro grain, entirely its own field
    rngr = np.random.default_rng((s ^ 0x52AA) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    brush = np.zeros((h, w), np.float32)
    for k in range(4):
        ang = rngr.uniform(0.0, np.pi)
        proj = (xx * np.cos(ang) + yy * np.sin(ang)) / mx
        ph = _msc(h, w, [max(7, int(mx * 0.08))], (s ^ 0x52BB) + 3 * k)
        brush += np.sin(proj * (140.0 + 50.0 * rngr.random()) + ph * 6.0)
    brush = brush / 4.0 * 0.5 + 0.5
    grain_r = _msc(h, w, [2, max(5, int(mx * 0.05)), max(11, int(mx * 0.2))], s ^ 0x52CC)
    R = 78.0 + brush * 78.0 + (grain_r - 0.5) * 70.0

    # Cc — the crack-valley glow web + its own pooling macro
    web = cv2.GaussianBlur(crack, (0, 0), max(1.0, mx * 0.004))
    pool_c = _msc(h, w, [max(9, int(mx * 0.12)), max(17, int(mx * 0.34))], s ^ 0x6CC3)
    Cc = 42.0 + web * 175.0 + (pool_c - 0.5) * 55.0

    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_ember_glass(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_1, seed)
    mx = float(max(h, w))
    crack, depth, flake, macro = _ember_glass_fields(h, w, s)
    # coarse silver flake bed (multi-scale sheen, no directional bias)
    sheen = _msc(h, w, [max(5, int(mx * 0.04)), max(11, int(mx * 0.12))], s ^ 0x9B01)
    metal_g = np.clip(0.66 + (sheen - 0.5) * 0.22 + flake * 0.30, 0.0, 1.0)
    metal = metal_g[:, :, None] * np.array([0.985, 0.975, 0.96], np.float32)
    # blood-orange -> crimson -> ember-black candy; cracks push toward crimson
    stops = [(0.93, 0.42, 0.06), (0.80, 0.16, 0.04), (0.52, 0.03, 0.07)]
    t = np.clip(macro * 0.75 + crack * 0.35, 0.0, 1.0)
    tint = _opt_oklch_ramp(stops, t, flatten_lightness=0.30, exact_edges=True)
    eff = candy_absorb(metal, tint, depth, density=1.0)
    # white-hot micro rim where the coat shears at crack edges (sharp accents)
    rim = _edge(crack, gain=5.0)
    eff = np.clip(eff + rim[:, :, None] * np.array([0.30, 0.12, 0.02], np.float32) * 0.55, 0.0, 1.0)
    eff = _upscale(eff.astype(np.float32), fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE — GLACIER CORE (fable_glacier_core)
# Arctic cyan→deep-sapphire Beer–Lambert candy over crushed-ice facets: a
# randomly-ROTATED Chebyshev (L∞) Voronoi makes ANGULAR shards (not round
# cells), each shard flat-shaded along its own random axis like a tipped ice
# face. The coat runs thin on shard faces and POOLS sapphire-dark in the
# fissures between shards (fissure web drives candy_absorb depth).
# Spec decorrelation: M = sparkle-gated shard-edge glints + its own glitter,
# R = its own 5-axis frost-feather grain, Cc = blurred deep-fissure cold glow
# + its own current field.
# UV-agnostic: per-shard random rotation AND random shading axis; isotropic
# statistics, no global direction anywhere.
# ============================================================================
FAB_2 = "fable_glacier_core"


def _glacier_core_shards(h, w, seed, count):
    """Rotated-Chebyshev Voronoi -> (facet shade, fissure web, cellA, cellB)."""
    mx = float(max(h, w))
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    py = rng.uniform(0, h, count).astype(np.float32)
    px = rng.uniform(0, w, count).astype(np.float32)
    th = rng.uniform(0.0, np.pi, count).astype(np.float32)       # shard rotation
    sc = rng.uniform(0.8, 1.25, count).astype(np.float32)        # shard size jitter
    ga = rng.uniform(0.0, 2.0 * np.pi, count).astype(np.float32) # facet shade axis
    ca = rng.random(count).astype(np.float32)
    cb = rng.random(count).astype(np.float32)
    # per-site scalar cos/sin (same values the old loop used elementwise)
    cs = np.array([np.cos(t) for t in th], np.float32)
    sn = np.array([np.sin(t) for t in th], np.float32)
    # rotated-Chebyshev*sc is within [0.566, 1.25]x Euclidean, so the true
    # top-2 sites always sit inside the 18 Euclidean-nearest candidates.
    # Inlined (instead of _opt_voro_top2 + callback) with in-place ufuncs:
    # identical op order per element -> bit-identical d1/d2/idx.
    from scipy.spatial import cKDTree
    tree = cKDTree(np.stack([py.astype(np.float64), px.astype(np.float64)], axis=1))
    K = min(18, count)
    d1 = np.empty((h, w), np.float32)
    d2 = np.empty((h, w), np.float32)
    idx = np.empty((h, w), np.int32)
    big = np.int32(1 << 30)
    step = max(16, int((4 << 20) // max(w * K, 1)))
    for y0 in range(0, h, step):
        y1 = min(y0 + step, h)
        yb = yy[y0:y1]
        xb = xx[y0:y1]
        _, cand = tree.query(np.stack([yb.ravel(), xb.ravel()], axis=1),
                             k=K, workers=-1)
        cand = cand.astype(np.int32).reshape(y1 - y0, w, K)
        dy = yb[:, :, None] - py[cand]
        dx = xb[:, :, None] - px[cand]
        csg = cs[cand]
        sng = sn[cand]
        u = dx * csg                  # u = (dx*cs) + (dy*sn), same order
        t1 = dy * sng
        u += t1
        np.multiply(dy, csg, out=t1)  # v = (dy*cs) - (dx*sn) == -dx*sn + dy*cs
        np.multiply(dx, sng, out=dx)
        t1 -= dx
        np.abs(u, out=u)
        np.abs(t1, out=t1)
        np.maximum(u, t1, out=u)
        u *= sc[cand]                 # u now holds dd
        two = np.partition(u, 1, axis=2)[:, :, :2]
        d1[y0:y1] = two[:, :, 0]
        d2[y0:y1] = two[:, :, 1]
        idx[y0:y1] = np.where(u <= two[:, :, :1], cand, big).min(axis=2)
    fissure = np.exp(-(d2 - d1) / (mx * 0.0075)).astype(np.float32)
    shade = ((xx - px[idx]) * np.cos(ga[idx]) + (yy - py[idx]) * np.sin(ga[idx])) / (mx * 0.10)
    shade = np.clip(shade * 0.5 + 0.5, 0.0, 1.0).astype(np.float32)
    return shade, fissure, ca[idx].astype(np.float32), cb[idx].astype(np.float32)


def _glacier_core_fields(h, w, seed):
    """-> (facet shade, fissure web, per-cell hue rand, candy depth, frost macro)."""
    mx = float(max(h, w))
    shade, fissure, ca, cb = _glacier_core_shards(h, w, seed ^ 0x61CE, 92)
    frostmac = _msc(h, w, [max(11, int(mx * 0.13)), max(19, int(mx * 0.32))], seed ^ 0x1CEB)
    depth = np.clip(0.30 + fissure * 2.7 + (1.0 - shade) * 0.30 + (cb - 0.5) * 0.5
                    + (frostmac - 0.5) * 0.30, 0.05, 3.4)
    return shade, fissure, ca, depth.astype(np.float32), frostmac


def _spec_fable_glacier_core(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_2, seed)
    mx = float(max(h, w))
    shade, fissure, _ca, _depth, _frostmac = _glacier_core_fields(h, w, s)

    # M — shard-edge glints (widened so they READ), sparkle-gated, + face glitter
    rngm = np.random.default_rng((s ^ 0x91F7) & 0x7FFFFFFF)
    edges = cv2.GaussianBlur(_edge(shade, gain=4.5), (0, 0), max(1.0, mx * 0.0016))
    edges = np.clip(edges * 3.0, 0.0, 1.0)
    gate = cv2.GaussianBlur(rngm.random((h, w)).astype(np.float32), (0, 0), 1.2)
    gate = np.clip((gate - 0.42) / 0.34, 0.0, 1.0)
    glit = np.clip((rngm.random((h, w)).astype(np.float32) - 0.965) / 0.035, 0.0, 1.0)
    patch_m = _msc(h, w, [max(15, int(mx * 0.2))], s ^ 0x91F8)
    M = 24.0 + edges * gate * 185.0 + glit * 200.0 + patch_m * 50.0

    # R — frost feather grain: 5 random feather axes of fine streaks + ice micro
    rngr = np.random.default_rng((s ^ 0xA3D9) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    feather = np.zeros((h, w), np.float32)
    for k in range(5):
        ang = rngr.uniform(0.0, np.pi)
        proj = (xx * np.cos(ang) + yy * np.sin(ang)) / mx
        ph = _msc(h, w, [max(5, int(mx * 0.045))], (s ^ 0xA3E0) + 3 * k)
        feather += np.sin(proj * (170.0 + 70.0 * rngr.random()) + ph * 9.0)
    feather = feather / 5.0 * 0.5 + 0.5
    ice_g = _msc(h, w, [2, max(7, int(mx * 0.07)), max(13, int(mx * 0.24))], s ^ 0xA3F1)
    R = 70.0 + feather * 72.0 + (ice_g - 0.5) * 76.0

    # Cc — cold glow pooled in the fissures + its own deep current field
    glow = cv2.GaussianBlur(fissure, (0, 0), max(1.0, mx * 0.005))
    current = _msc(h, w, [max(9, int(mx * 0.1)), max(17, int(mx * 0.3))], s ^ 0xC01D)
    Cc = 40.0 + glow * 168.0 + (current - 0.5) * 58.0

    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_glacier_core(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_2, seed)
    mx = float(max(h, w))
    shade, fissure, ca, depth, frostmac = _glacier_core_fields(h, w, s)
    # icy silver bed: per-facet flat shading + frost sparkle
    rngp = np.random.default_rng((s ^ 0xB10C) & 0x7FFFFFFF)
    fl = cv2.GaussianBlur(rngp.random((h, w)).astype(np.float32), (0, 0), 0.65)
    sparkle = np.clip((fl - 0.70) / 0.30, 0.0, 1.0) ** 1.8
    metal_g = np.clip(0.58 + (shade - 0.5) * 0.34 + sparkle * 0.26, 0.0, 1.0)
    metal = metal_g[:, :, None] * np.array([0.94, 0.985, 1.0], np.float32)
    # arctic cyan -> azure -> deep sapphire; per-shard hue + frost-macro drift
    stops = [(0.30, 0.95, 0.98), (0.05, 0.55, 0.90), (0.04, 0.16, 0.60)]
    t = np.clip(ca * 0.62 + frostmac * 0.38, 0.0, 1.0)
    tint = _opt_oklch_ramp_exact(stops, t, flatten_lightness=0.45)  # bit-exact:
    # glacier's sapphire tint rides R~0 where the gamut bisection is ulp-
    # unstable AND candy log-amplifies — only exact evaluation matches.
    eff = candy_absorb(metal, tint, depth, density=1.0)
    # cold bright rims where shard faces meet (sharp accents)
    rim = _edge(shade, gain=4.0)
    eff = np.clip(eff + rim[:, :, None] * np.array([0.10, 0.20, 0.26], np.float32) * 0.5, 0.0, 1.0)
    eff = _upscale(eff.astype(np.float32), fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE — ABYSS LANTERN (fable_abyss_lantern)
# Near-black deep-sea teal absorption: Beer–Lambert depth ~1.0–2.5 EVERYWHERE,
# the gunmetal bed barely surviving the dive. Scattered radial lantern cells
# live ALMOST ONLY in the clearcoat channel — invisible head-on, they bloom
# under raking light (angle reveal). The paint carries only a faint teal hint
# of each lantern (slightly thinner coat at the cores + membrane ring kiss).
# Spec decorrelation: M = sparse plankton micro-glints (own scatter) + drift,
# R = its own abyssal-silt grain, Cc = THE lantern glow + membrane rings.
# UV-agnostic: radial cells at scattered centers, isotropic murk, 3 random
# current axes; no global gradient.
# ============================================================================
FAB_3 = "fable_abyss_lantern"


def _abyss_lantern_cells(h, w, seed, count):
    """Scattered radial lantern cells -> (soft glow, membrane rings)."""
    mx = float(max(h, w))
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    glow = np.zeros((h, w), np.float32)
    ring = np.zeros((h, w), np.float32)
    for _ in range(count):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        rad = rng.uniform(0.045, 0.105) * mx
        amp = rng.uniform(0.55, 1.0)
        ph = rng.uniform(0.0, 2.0 * np.pi)
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, 2.8 * rad)   # body tail < 4e-4
        rr = np.sqrt((yy[y0:y1, x0:x1] - cy) ** 2 + (xx[y0:y1, x0:x1] - cx) ** 2)
        body = np.exp(-(rr / rad) ** 2) * amp
        flick = 0.7 + 0.3 * np.sin(rr / rad * 9.0 + ph)      # radial flicker, orientation-free
        glow[y0:y1, x0:x1] += body * flick
        ring[y0:y1, x0:x1] += np.exp(-(((rr - rad * 0.72) / (rad * 0.085)) ** 2)) * amp
    return np.clip(glow, 0.0, 1.6).astype(np.float32), np.clip(ring, 0.0, 1.2).astype(np.float32)


def _abyss_lantern_fields(h, w, seed):
    """-> (lantern glow, membrane rings, murk macro, multi-angle currents)."""
    mx = float(max(h, w))
    glow, ring = _abyss_lantern_cells(h, w, seed ^ 0xAB15, 24)
    murk = _msc(h, w, [max(13, int(mx * 0.16)), max(23, int(mx * 0.4))], seed ^ 0x0DEE)
    rng = np.random.default_rng((seed ^ 0xC4BD) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    cur = np.zeros((h, w), np.float32)
    for k in range(3):
        ang = rng.uniform(0.0, np.pi)
        proj = (xx * np.cos(ang) + yy * np.sin(ang)) / mx
        ph = _msc(h, w, [max(9, int(mx * 0.12))], (seed ^ 0xC4C0) + 7 * k)
        cur += np.sin(proj * (34.0 + 14.0 * rng.random()) + ph * 7.0)
    cur = cur / 3.0 * 0.5 + 0.5
    return glow, ring, murk, cur.astype(np.float32)


def _spec_fable_abyss_lantern(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_3, seed)
    mx = float(max(h, w))
    glow, ring, _murk, _cur = _abyss_lantern_fields(h, w, s)

    # M — sparse plankton micro-glints (own scatter) + faint drift patches
    rngm = np.random.default_rng((s ^ 0x9A4F) & 0x7FFFFFFF)
    pk = rngm.random((h, w)).astype(np.float32)
    plank = np.clip((pk - 0.985) / 0.015, 0.0, 1.0)
    plank = np.clip(cv2.GaussianBlur(plank, (0, 0), 0.8) * 3.0, 0.0, 1.0)
    drift = _msc(h, w, [max(11, int(mx * 0.14)), max(19, int(mx * 0.36))], s ^ 0x9A50)
    M = 16.0 + plank * 210.0 + drift * 32.0

    # R — abyssal silt: its own flowing grain (micro + mid + macro swell)
    silt = _msc(h, w, [2, max(6, int(mx * 0.05)), max(13, int(mx * 0.2))], s ^ 0x517E)
    swell = _msc(h, w, [max(17, int(mx * 0.3))], s ^ 0x517F)
    R = 64.0 + silt * 66.0 + (swell - 0.5) * 80.0

    # Cc — THE lantern layer: glow blooms + membrane rings (angle reveal)
    Cc = 44.0 + np.clip(glow, 0.0, 1.25) * 145.0 + ring * 48.0

    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_abyss_lantern(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_3, seed)
    mx = float(max(h, w))
    glow, ring, murk, cur = _abyss_lantern_fields(h, w, s)
    # gunmetal bed with rare flake survivors
    rngp = np.random.default_rng((s ^ 0x5EA1) & 0x7FFFFFFF)
    fl = cv2.GaussianBlur(rngp.random((h, w)).astype(np.float32), (0, 0), 0.7)
    flake = np.clip((fl - 0.80) / 0.20, 0.0, 1.0) ** 1.7
    metal_g = np.clip(0.42 + (murk - 0.5) * 0.10 + flake * 0.24 + (cur - 0.5) * 0.08, 0.0, 1.0)
    metal = metal_g[:, :, None] * np.array([0.92, 1.0, 0.99], np.float32)
    # deep-sea teal absorption, drifting with murk + currents
    stops = [(0.05, 0.66, 0.60), (0.03, 0.46, 0.50), (0.04, 0.30, 0.42)]
    t = np.clip(murk * 0.7 + cur * 0.3, 0.0, 1.0)
    tint = _opt_oklch_ramp(stops, t, flatten_lightness=0.25, exact_edges=True)
    depth = np.clip(1.30 + (murk - 0.5) * 0.8 + (cur - 0.5) * 0.35
                    - np.clip(glow, 0.0, 1.0) * 0.55, 0.65, 2.5)
    eff = candy_absorb(metal, tint, depth, density=1.0)
    # the faint hint: membrane rings + lantern cores barely kiss the paint
    hint = np.clip(ring * 0.6 + np.clip(glow - 0.8, 0.0, 1.0) * 0.5, 0.0, 1.0)
    eff = np.clip(eff + hint[:, :, None] * np.array([0.02, 0.10, 0.09], np.float32) * 0.5, 0.0, 1.0)
    eff = _upscale(eff.astype(np.float32), fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE — STAINED AURORA (fable_stained_aurora)
# Leaded stained glass under aurora light: flow-warped Voronoi panes where
# EACH pane samples its own jewel hue from a per-cell random t on an OKLCH
# ramp (per-cell lookup through the cell index map), with per-cell
# Beer–Lambert depth so every pane is deep candy glass that POOLS darker
# toward its lead border (border-halo depth term). Dark matte lead lines
# between panes; per-pane concentric hand-rolled-glass ripple.
# Spec decorrelation BY CONSTRUCTION: M/R/Cc each own a tri_partition
# territory + their own motif (starburst glints / hammered grain / aurora
# pooling).
# UV-agnostic: scattered warped cells, per-cell radial ripple, no global axis.
# ============================================================================
FAB_4 = "fable_stained_aurora"


def _stained_aurora_panes(h, w, seed, count):
    """Flow-warped Euclidean Voronoi -> (d1/mx, gap/mx, cell index map)."""
    mx = float(max(h, w))
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    wy = (_msc(h, w, [max(9, int(mx * 0.09)), max(17, int(mx * 0.26))], seed ^ 0x70AA) - 0.5) * mx * 0.07
    wx = (_msc(h, w, [max(9, int(mx * 0.09)), max(17, int(mx * 0.26))], seed ^ 0x70BB) - 0.5) * mx * 0.07
    yw = yy + wy
    xw = xx + wx
    py = rng.uniform(0, h, count).astype(np.float32)
    px = rng.uniform(0, w, count).astype(np.float32)
    d1, d2, idx = _opt_voro_top2(yw, xw, py, px)  # bit-identical to the loop
    d1 = np.sqrt(d1)
    gap = (np.sqrt(d2) - d1) / mx
    return (d1 / mx).astype(np.float32), gap.astype(np.float32), idx


def _stained_aurora_fields(h, w, seed):
    """-> (lead lines, border pool halo, glass ripple, per-pane t, depth, aurora)."""
    mx = float(max(h, w))
    n = 64
    d1n, gapn, idx = _stained_aurora_panes(h, w, seed ^ 0x57A1, n)
    rngc = np.random.default_rng((seed ^ 0xCE11) & 0x7FFFFFFF)
    tc = rngc.random(n).astype(np.float32)                   # per-pane jewel hue t
    dc = rngc.uniform(0.7, 2.1, n).astype(np.float32)        # per-pane candy depth
    phc = rngc.uniform(0.0, 2.0 * np.pi, n).astype(np.float32)
    lead = np.exp(-gapn / 0.0055).astype(np.float32)         # ~11 px canvas lead lines
    pool = np.exp(-gapn / 0.030).astype(np.float32)          # wider halo: pools at borders
    ripple = (np.sin(d1n / 0.0019 + phc[idx]) * 0.5 + 0.5).astype(np.float32)
    aur = _msc(h, w, [max(11, int(mx * 0.14)), max(21, int(mx * 0.36))], seed ^ 0x57F3)
    t_pane = np.clip(tc[idx] + (aur - 0.5) * 0.16, 0.0, 1.0).astype(np.float32)
    depth = np.clip(dc[idx] * (0.55 + 0.5 * pool) + (ripple - 0.5) * 0.30, 0.10, 3.2).astype(np.float32)
    return lead, pool, ripple, t_pane, depth, aur


def _spec_fable_stained_aurora(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_4, seed)
    mx = float(max(h, w))
    lead, _pool, ripple, _t_pane, _depth, _aur = _stained_aurora_fields(h, w, s)
    m0, m1, m2 = tri_partition((h, w), s ^ 0x3717, cells=150, soften_px=2.0)

    # M — territory 0: glass starburst glints + ripple sheen; lead stays dull
    rngm = np.random.default_rng((s ^ 0xD0D0) & 0x7FFFFFFF)
    g = cv2.GaussianBlur(rngm.random((h, w)).astype(np.float32), (0, 0), 0.6)
    star = np.clip((g - 0.78) / 0.22, 0.0, 1.0) ** 2.0
    M = (26.0 + m0 * (95.0 + star * 130.0 + ripple * 45.0) + star * 30.0) * (1.0 - lead * 0.80)

    # R — territory 1: hammered-glass grain (own multiscale field); lead = matte
    ham = _msc(h, w, [3, max(7, int(mx * 0.06)), max(15, int(mx * 0.22))], s ^ 0xE1E1)
    R = 58.0 + m1 * (50.0 + ham * 95.0) + (ham - 0.5) * 26.0 + lead * 95.0

    # Cc — territory 2: aurora pooling motif (own slow field)
    pool2 = _msc(h, w, [max(9, int(mx * 0.11)), max(19, int(mx * 0.34))], s ^ 0xF2F2)
    Cc = 40.0 + m2 * (70.0 + pool2 * 120.0) + pool2 * 28.0

    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_stained_aurora(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_4, seed)
    mx = float(max(h, w))
    lead, pool, ripple, t_pane, depth, aur = _stained_aurora_fields(h, w, s)
    # silver-leaf bed behind the glass, rippled like hand-rolled panes
    rngp = np.random.default_rng((s ^ 0x1EAF) & 0x7FFFFFFF)
    fl = cv2.GaussianBlur(rngp.random((h, w)).astype(np.float32), (0, 0), 0.7)
    sparkle = np.clip((fl - 0.72) / 0.28, 0.0, 1.0) ** 1.7
    metal_g = np.clip(0.62 + (ripple - 0.5) * 0.18 + sparkle * 0.24, 0.0, 1.0)
    metal = metal_g[:, :, None] * np.array([0.99, 0.985, 0.97], np.float32)
    # jewel ramp: ruby -> amber -> emerald -> sapphire -> violet, per-pane t
    stops = [(0.66, 0.04, 0.12), (0.97, 0.58, 0.08), (0.06, 0.58, 0.27),
             (0.05, 0.24, 0.78), (0.46, 0.10, 0.66)]
    tint = _opt_oklch_ramp(stops, t_pane, flatten_lightness=0.55, exact_edges=True)
    eff = candy_absorb(metal, tint, depth, density=1.0)
    # dark matte lead between panes
    leadm = np.clip(lead * 1.25, 0.0, 1.0)[:, :, None]
    eff = eff * (1.0 - leadm) + np.array([0.085, 0.085, 0.10], np.float32) * leadm
    eff = _upscale(np.clip(eff, 0.0, 1.0).astype(np.float32), fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE 5) PRISM VEIL — quantized thin-film interference orders drifting over
# a near-black cherry base. Thickness = 4-random-axis interference flow + fine
# ripple; banded Newton orders (quantize 0.78), veiled by scattered radial
# patches. Spec: M flares ONLY on the quantized order edges, R rides its own
# satin field, Cc pools on a separate slow-flow order plateau.
# ============================================================================
FAB_5 = "fable_prism_veil"


def _prism_veil_splat(acc, yy, xx, cy, cx, rad, ang, amp):
    """Soft radial veil patch (isotropic gaussian — rotation-free, UV-agnostic)."""
    r2 = (yy - cy) ** 2 + (xx - cx) ** 2
    sig = rad * 4.5
    acc += np.exp(-r2 / (2.0 * sig * sig)).astype(np.float32) * amp


def _prism_veil_fields(h, w, seed):
    m = float(max(h, w))
    rng = np.random.default_rng((seed ^ 0x5A11) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    flow = np.zeros((h, w), np.float32)
    for _k in range(4):                                # 4 random interference axes
        ang = rng.uniform(0.0, 2.0 * np.pi)
        wl = rng.uniform(0.17, 0.36) * m
        ph = rng.uniform(0.0, 2.0 * np.pi)
        wgt = rng.uniform(0.6, 1.0)
        proj = np.cos(ang) * xx + np.sin(ang) * yy
        flow += (np.sin(proj * (2.0 * np.pi / wl) + ph) * wgt).astype(np.float32)
    flow = ((flow - flow.min()) / max(float(flow.max() - flow.min()), 1e-6)).astype(np.float32)
    ripple = _msc(h, w, [5, 11], seed ^ 0x5A12)        # fine film shimmer (micro band)
    macro = _msc(h, w, [170, 360], seed ^ 0x5A15)      # spreads regions across orders
    thickness = np.clip(flow * 0.52 + macro * 0.34 + (ripple - 0.5) * 0.20, 0.0, 1.0).astype(np.float32)
    veil = np.clip(_opt_scatter_field(h, w, seed ^ 0x5A13, 30, _prism_veil_splat,
                                      lambda rad: 3.4 * (rad * 4.5)), 0.0, 1.0) ** 1.2
    veil = (0.08 + 0.92 * veil).astype(np.float32)     # scattered veil patches; cherry shows between
    flake = _msc(h, w, [2, 4], seed ^ 0x5A14)          # cherry micro flake
    return thickness, flow, veil, flake


def _spec_fable_prism_veil(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_5, seed)
    thickness, flow, veil, flake = _prism_veil_fields(h, w, s)
    q = np.floor(thickness * 4.0).astype(np.float32)
    edge = _edge(q * 0.5, gain=3.0)                    # M: bright-order band EDGES only
    satin = _msc(h, w, [17, 41, 95], s ^ 0x5A21)       # R: its own satin field
    pool_t = flow * 1.8                                # Cc: slow flow at a DIFFERENT order count
    pool_fr = pool_t - np.floor(pool_t)
    pool = (np.clip(1.0 - np.abs(pool_fr - 0.5) * 2.0, 0.0, 1.0) ** 1.5).astype(np.float32)
    glow = _msc(h, w, [55, 130], s ^ 0x5A22)
    M = 24.0 + edge * 192.0 * veil + flake * 26.0 + np.mod(q, 2.0) * 22.0 * veil
    R = 168.0 - satin * 118.0 - edge * 22.0
    Cc = 30.0 + pool * 118.0 * veil + glow * 44.0
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_prism_veil(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_5, seed)
    thickness, _flow, veil, flake = _prism_veil_fields(h, w, s)
    film = interference_palette(thickness, orders=4.0, quantize=0.78, brightness=0.92)
    cherry = np.empty((h, w, 3), np.float32)           # near-black cherry, flake-lifted
    cherry[:, :, 0] = 0.052 + flake * 0.045
    cherry[:, :, 1] = 0.006 + flake * 0.012
    cherry[:, :, 2] = 0.016 + flake * 0.020
    wgt = (veil * 0.92)[:, :, None]
    eff = np.clip(cherry + film * wgt, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE 6) OILFORGE — oil-slick interference rings blooming around scattered
# heat epicenters on brushed gunmetal. Brush grain runs at 3 DIFFERENT random
# angles in Voronoi territories (tri_partition); ring thickness decays from
# each epicenter and is quantized into Newton orders. Spec: M = ring crests,
# R = the multi-angle brush grain, Cc = heat-center glow on its own pooling.
# ============================================================================
FAB_6 = "fable_oilforge"


def _oilforge_scratch(h, w, ang, seed):
    """Fine brushed-metal scratch profile along angle ang with coarse wobble."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    v = (-np.sin(ang) * xx + np.cos(ang) * yy) * (1024.0 / m)
    wob = (_msc(h, w, [80, 190], seed ^ 0x6F01) - 0.5) * 7.0
    prof = rng.random(4096).astype(np.float32)
    idx = np.mod((v + wob) * 0.85, 4096.0).astype(np.int32)
    g = prof[idx]
    return (0.62 * g + 0.38 * _msc(h, w, [2, 5], seed ^ 0x6F02)).astype(np.float32)


def _oilforge_fields(h, w, seed):
    m = float(max(h, w))
    rng = np.random.default_rng((seed ^ 0x6F10) & 0x7FFFFFFF)
    # 3 brush-angle territories — multi-angle by construction, never one direction
    p0, p1, p2 = tri_partition((h, w), seed ^ 0x6F11, cells=54, soften_px=max(2.0, m / 300.0))
    angs = rng.uniform(0.0, np.pi, 3)
    grain = (p0 * _oilforge_scratch(h, w, float(angs[0]), seed ^ 0x6F21)
             + p1 * _oilforge_scratch(h, w, float(angs[1]), seed ^ 0x6F22)
             + p2 * _oilforge_scratch(h, w, float(angs[2]), seed ^ 0x6F23)).astype(np.float32)
    yy, xx, _, _ = _coords(h, w)
    thick = np.zeros((h, w), np.float32)
    halo = np.zeros((h, w), np.float32)
    n = int(rng.integers(9, 14))                       # scattered heat epicenters
    for _i in range(n):
        cy = rng.uniform(0.0, h)
        cx = rng.uniform(0.0, w)
        reach = rng.uniform(0.075, 0.16) * m
        r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
        np.maximum(thick, np.exp(-r / reach).astype(np.float32), out=thick)
        halo += np.exp(-((r / (reach * 1.45)) ** 2)).astype(np.float32) * 0.7
    halo = np.clip(halo, 0.0, 1.0)
    return grain, thick, halo


def _spec_fable_oilforge(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_6, seed)
    grain, thick, halo = _oilforge_fields(h, w, s)
    pres = np.clip((thick - 0.07) * 6.5, 0.0, 1.0)
    bands = thick * 5.5
    frac = (bands - np.floor(bands)).astype(np.float32)
    crest = (np.exp(-((frac - 0.55) / 0.10) ** 2) * pres).astype(np.float32)  # M: ring crests
    glint = _msc(h, w, [2, 4], s ^ 0x6F31)
    pool = _msc(h, w, [48, 110], s ^ 0x6F32)
    M = 26.0 + crest * 198.0 + glint * 26.0
    R = 178.0 - grain * 122.0 - crest * 18.0           # R: own multi-angle brush grain
    Cc = 28.0 + halo * 128.0 + pool * 46.0             # Cc: heat-center glow, own pooling
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_oilforge(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_6, seed)
    grain, thick, halo = _oilforge_fields(h, w, s)
    film = interference_palette(thick, orders=5.5, quantize=0.72, brightness=1.0)
    gm = (0.115 + grain * 0.155)[:, :, None] * np.array([0.94, 0.985, 1.07], np.float32)
    presw = (np.clip((thick - 0.07) * 6.5, 0.0, 1.0) * (0.50 + 0.40 * halo))[:, :, None]
    eff = np.clip(gm * (1.0 - presw * 0.80) + film * presw * 0.92, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE 7) TEMPERED DAWN — titanium weld-temper. Scattered random-walk weld
# arcs (cv2 polylines -> distance transform); quantized straw-bronze-violet-
# blue temper orders trace each path's heat falloff; brushed raw titanium
# crosshatch between paths. Spec: M = weld bead lines, R = its own crosshatch
# grain (different axes than the paint's), Cc = heat-affected-zone halo.
# ============================================================================
FAB_7 = "fable_tempered_dawn"


def _tempered_dawn_hatch(h, w, seed):
    """Crosshatch raw-titanium grain: 3 random-axis scratch sets, max-combined."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    g = np.zeros((h, w), np.float32)
    warp = (_msc(h, w, [60, 140], seed ^ 0x7D02) - 0.5) * 9.0
    for _k in range(3):
        ang = rng.uniform(0.0, np.pi)
        period = rng.uniform(2.1, 3.9) * (m / 1024.0)
        ph = rng.uniform(0.0, 2.0 * np.pi)
        proj = np.cos(ang) * xx + np.sin(ang) * yy
        srt = 0.5 + 0.5 * np.sin((proj + warp) * (2.0 * np.pi / period) + ph)
        np.maximum(g, (srt ** 3).astype(np.float32), out=g)
    return (0.72 * g + 0.28 * _msc(h, w, [2, 5], seed ^ 0x7D03)).astype(np.float32)


def _tempered_dawn_fields(h, w, seed):
    m = float(max(h, w))
    rng = np.random.default_rng((seed ^ 0x7D10) & 0x7FFFFFFF)
    path = np.zeros((h, w), np.uint8)
    n_welds = int(rng.integers(7, 12))                 # scattered curved weld paths
    for _i in range(n_welds):
        steps = int(rng.integers(26, 40))
        heading = rng.uniform(0.0, 2.0 * np.pi) + np.cumsum(rng.normal(0.0, 0.17, steps))
        step_len = rng.uniform(0.012, 0.020) * m
        py = rng.uniform(0.08, 0.92) * h + np.cumsum(np.sin(heading) * step_len)
        px = rng.uniform(0.08, 0.92) * w + np.cumsum(np.cos(heading) * step_len)
        pts = np.stack([np.clip(px, 1, w - 2), np.clip(py, 1, h - 2)], axis=1)
        pts = pts.astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(path, [pts], False, 255, thickness=max(1, int(round(m / 480.0))))
    dist = cv2.distanceTransform((255 - path).astype(np.uint8), cv2.DIST_L2, 3).astype(np.float32)
    heat = np.exp(-dist / (0.042 * m)).astype(np.float32)     # temper thickness driver
    bead = np.exp(-((dist / (0.0042 * m)) ** 2)).astype(np.float32)  # tight weld bead line
    halo = np.exp(-dist / (0.075 * m)).astype(np.float32)     # broad heat-affected zone
    return heat, bead, halo


def _spec_fable_tempered_dawn(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_7, seed)
    heat, bead, halo = _tempered_dawn_fields(h, w, s)
    hatch_s = _tempered_dawn_hatch(h, w, s ^ 0x7D40)   # R: OWN crosshatch (own axes)
    glint = _msc(h, w, [2, 4], s ^ 0x7D41)
    pooln = _msc(h, w, [52, 120], s ^ 0x7D42)
    M = 24.0 + bead * 212.0 + glint * 24.0             # M: weld bead lines flare
    R = 172.0 - hatch_s * 118.0 - bead * 26.0
    Cc = 30.0 + halo * 122.0 + pooln * 44.0            # Cc: HAZ halo + own pooling
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_tempered_dawn(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_7, seed)
    heat, bead, _halo = _tempered_dawn_fields(h, w, s)
    hatch = _tempered_dawn_hatch(h, w, s ^ 0x7D30)
    film = interference_palette(heat ** 0.65, orders=2.4, quantize=0.72, brightness=0.95)
    ti = (0.30 + hatch * 0.24)[:, :, None] * np.array([1.02, 0.98, 0.92], np.float32)
    presw = np.clip((heat - 0.07) * 7.0, 0.0, 1.0)[:, :, None]
    eff = ti * (1.0 - presw * 0.82) + film * presw * 0.90
    beadw = (bead * 0.88)[:, :, None]
    eff = eff * (1.0 - beadw) + np.array([0.86, 0.87, 0.90], np.float32) * beadw
    eff = np.clip(eff, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE 8) PULSE ALLOY — concentric pulse rings from MANY scattered centers
# (nearest-center ownership -> crisp cellular ring cells); the INTEGER ring
# order picks the hue by sampling an OKLCH ramp at quantized steps; brushed
# alloy + faint quantized interference sheen between rings. Spec: M = ring
# crests of center-set 1, R = inter-ring grain (own noise), Cc = soft pulse
# glow from center-set 2 (DIFFERENT centers).
# ============================================================================
FAB_8 = "fable_pulse_alloy"


def _pulse_alloy_fields(h, w, seed):
    m = float(max(h, w))
    yy, xx, _, _ = _coords(h, w)
    rng = np.random.default_rng((seed ^ 0x8A10) & 0x7FFFFFFF)
    cys = np.empty(16, np.float32)
    cxs = np.empty(16, np.float32)
    wds = np.empty(16, np.float32)
    phs = np.empty(16, np.float32)
    for _i in range(16):                               # center-set 1: pulse sources
        cys[_i] = rng.uniform(0.0, h)
        cxs[_i] = rng.uniform(0.0, w)
        wds[_i] = rng.uniform(0.030, 0.062) * m
        phs[_i] = rng.uniform(0.0, 1.0)
    # nearest-center ownership + the owner's ring phase (same f32 math as the
    # old running-min loop, evaluated on cKDTree candidates — bit-identical)
    dsq, _, own = _opt_voro_top2(yy, xx, cys, cxs, k=4)
    ringv = (np.sqrt(dsq) / wds[own] + phs[own]).astype(np.float32)
    ring_idx = np.floor(ringv).astype(np.float32)
    frac = (ringv - ring_idx).astype(np.float32)
    rng2 = np.random.default_rng((seed ^ 0x8A20) & 0x7FFFFFFF)
    glow = np.zeros((h, w), np.float32)
    for _i in range(15):                               # center-set 2: glow (different!)
        cy = rng2.uniform(0.0, h)
        cx = rng2.uniform(0.0, w)
        reach = rng2.uniform(0.09, 0.20) * m
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, 3.4 * reach)  # tail < 0.004
        r2 = (yy[y0:y1, x0:x1] - cy) ** 2 + (xx[y0:y1, x0:x1] - cx) ** 2
        glow[y0:y1, x0:x1] += (np.exp(-r2 / (2.0 * reach * reach)).astype(np.float32)
                               * rng2.uniform(0.5, 0.9))
    glow = np.clip(glow, 0.0, 1.0)
    grain = _msc(h, w, [2, 5, 12], seed ^ 0x8A30)      # alloy micro/mid grain
    return ring_idx, frac, glow, grain


def _spec_fable_pulse_alloy(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_8, seed)
    ring_idx, frac, glow, _grain = _pulse_alloy_fields(h, w, s)
    pulse = (0.25 + 0.75 * np.exp(-ring_idx * 0.16)).astype(np.float32)
    bandm = (np.clip((0.38 - frac) * 12.0, 0.0, 1.0) * pulse).astype(np.float32)
    crest = (np.exp(-((frac - 0.19) / 0.07) ** 2) * pulse).astype(np.float32)
    glint = _msc(h, w, [2, 4], s ^ 0x8A50)
    rg = _msc(h, w, [3, 7, 16], s ^ 0x8A51)            # R: inter-ring grain, own noise
    slow = _msc(h, w, [58, 135], s ^ 0x8A52)
    M = 26.0 + crest * 202.0 + glint * 24.0            # M: ring crests of center-set 1
    R = 172.0 - rg * 124.0 - bandm * 18.0
    Cc = 30.0 + glow * 128.0 + slow * 42.0             # Cc: pulse glow from center-set 2
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_pulse_alloy(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_8, seed)
    ring_idx, frac, _glow, grain = _pulse_alloy_fields(h, w, s)
    t = np.mod(ring_idx * 2.0, 7.0) / 6.0              # quantized ramp steps, strided so
    # adjacent ring orders land on CONTRASTING hues (full palette near each center)
    cols = _opt_oklch_ramp([(0.00, 0.42, 0.47), (0.14, 0.22, 0.84),
                       (0.78, 0.10, 0.56), (0.99, 0.63, 0.12)],
                      t, flatten_lightness=0.55)
    pulse = (0.25 + 0.75 * np.exp(-ring_idx * 0.16)).astype(np.float32)
    bandm = (np.clip((0.38 - frac) * 12.0, 0.0, 1.0) * pulse)[:, :, None]
    alloy = (0.27 + grain * 0.26)[:, :, None] * np.array([0.965, 0.985, 1.03], np.float32)
    sheen_t = _msc(h, w, [130, 290], s ^ 0x8A40)
    sheen = interference_palette(sheen_t, orders=1.4, quantize=0.60, brightness=0.42)
    eff = alloy * (1.0 - bandm) + cols * bandm + sheen * (1.0 - bandm) * 0.18
    eff = np.clip(eff, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# ===== FABLE: VELVET ECLIPSE (FAB_9) =========================================
# Perceptual color flip — dead-matte indigo velvet interleaved at flake scale
# with mirror molten gold. The gold fraction breathes through scattered molten
# pools (mid/macro band) so head-on the car reads indigo velvet and raking sun
# flares the lattice awake. Scattered eclipse coronas live in the clearcoat on
# their OWN centers: rings of wet glow with umbral discs that drink it down.
# Three unrelated primary spec geometries: pool-thresholded micro lattice (M),
# 4-random-axis fibre nap (R), scattered ring+umbra system (Cc).
# ============================================================================
FAB_9 = "fable_velvet_eclipse"


def _velvet_eclipse_coronas(h, w, seed):
    """Scattered eclipse rings: thin annulus with a crisp rim + a soft umbral
    disc inside each. Own centers/radii — this is Cc's primary geometry."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    rings = np.zeros((h, w), np.float32)
    umbra = np.zeros((h, w), np.float32)
    for _ in range(15):
        cy = rng.uniform(0.0, h)
        cx = rng.uniform(0.0, w)
        rad = rng.uniform(0.055, 0.170) * m
        wid = rng.uniform(0.010, 0.022) * m
        amp = rng.uniform(0.55, 1.0)
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, max(rad + 4.0 * wid, rad * 1.32))
        d = np.sqrt((yy[y0:y1, x0:x1] - cy) ** 2 + (xx[y0:y1, x0:x1] - cx) ** 2)
        soft = np.exp(-(((d - rad) / wid) ** 2))
        crisp = np.clip(1.0 - np.abs(d - rad) / (wid * 0.45), 0.0, 1.0)
        rsub = rings[y0:y1, x0:x1]
        np.maximum(rsub, amp * np.clip(soft * 0.70 + crisp * 0.55, 0.0, 1.0), out=rsub)
        usub = umbra[y0:y1, x0:x1]
        np.maximum(usub, amp * 0.85 * np.exp(-((d / (rad * 0.72)) ** 4)), out=usub)
    return rings.astype(np.float32), umbra.astype(np.float32)


@_memo_fields
def _velvet_eclipse_fields(h, w, seed):
    m = float(max(h, w))
    sr = m / 1024.0
    # molten pools (mid + macro bands) — where the gold lattice runs dense
    pool = _msc(h, w, [max(3, int(33 * sr)), max(9, int(97 * sr)), max(21, int(219 * sr))],
                seed ^ 0x1A2B3C)
    pool = np.clip((pool - 0.46) * 2.6 + 0.5, 0.0, 1.0)
    pool = (pool * pool * (3.0 - 2.0 * pool)).astype(np.float32)
    # micro flip lattice with pool-driven local gold density (own threshold map:
    # sparse lone flecks in open velvet, dense molten weave inside the pools)
    rng = np.random.default_rng((seed ^ 0x4D5E6F) & 0x7FFFFFFF)
    micro = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32), (0, 0), max(0.8, 1.1 * sr))
    lo = float(np.quantile(micro, 0.30))
    hi = float(np.quantile(micro, 0.985))
    thr = hi - (hi - lo) * (0.10 + 0.80 * pool)
    gold = np.clip((micro - thr) / max(0.06 * (hi - lo), 1e-5), 0.0, 1.0).astype(np.float32)
    # molten flow (micro/mid tonal life inside the gold)
    flow = _msc(h, w, [max(2, int(5 * sr)), max(5, int(15 * sr)), max(13, int(43 * sr))],
                seed ^ 0x70819A).astype(np.float32)
    # velvet nap — R's OWN field: 4 random-axis fine fibres, flow-wobbled
    arng = np.random.default_rng((seed ^ 0x92A3B4) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    napsum = np.zeros((h, w), np.float32)
    for _ in range(4):
        ang = arng.uniform(0.0, np.pi)
        per = max(1.6, arng.uniform(2.6, 6.0) * sr)
        ph = (xx * np.cos(ang) + yy * np.sin(ang)) / per
        napsum += np.sin(2.0 * np.pi * ph + arng.uniform(0.0, 6.283) + flow * arng.uniform(2.5, 6.0))
    nap = np.clip(0.5 + napsum * 0.27, 0.0, 1.0).astype(np.float32)
    rings, umbra = _velvet_eclipse_coronas(h, w, (seed ^ 0xC5D6E7) & 0x7FFFFFFF)
    return gold, pool, flow, nap, rings, umbra


def _spec_fable_velvet_eclipse(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_9, seed)
    gold, pool, flow, nap, rings, umbra = _velvet_eclipse_fields(h, w, s)
    g1 = np.random.default_rng((s ^ 0x0DDB17) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    g2 = np.random.default_rng((s ^ 0x0FACE5) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    g3 = np.random.default_rng((s ^ 0x0BEAD9) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    # M — PRIMARY: the gold lattice. Near-max mirror in gold; dead velvet floor
    # elsewhere except rare lone flecks so raking sun still twinkles the dark.
    pins = np.clip(cv2.GaussianBlur((g2 > 0.9988).astype(np.float32), (0, 0), 0.6) * 4.0, 0.0, 1.0)
    M = 20.0 + 228.0 * gold * (0.80 + 0.20 * flow) + 150.0 * pins * (1.0 - gold)
    # R — PRIMARY: the velvet nap (own 4-axis fibre field): matte-high velvet
    # with sheen lanes; the gold only tugs R down as a modest cross-term.
    R = 92.0 + 118.0 * nap - 54.0 * gold + 24.0 * (g1 - 0.5)
    # Cc — PRIMARY: eclipse coronas. Wet glow rides the rings, the umbral discs
    # drink the clearcoat down; faint micro breath keeps it alive between.
    Cc = 62.0 + 172.0 * rings - 38.0 * umbra + 16.0 * (g3 - 0.5)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_velvet_eclipse(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_9, seed)
    gold, pool, flow, nap, rings, umbra = _velvet_eclipse_fields(h, w, s)
    # indigo velvet body — nap-lit OKLab ramp (navy depths -> electric indigo)
    t_v = np.clip(0.08 + 0.52 * nap + 0.30 * pool, 0.0, 1.0)
    velvet = _opt_oklch_ramp([(0.045, 0.035, 0.150), (0.115, 0.085, 0.360), (0.215, 0.150, 0.560)],
                        t_v, flatten_lightness=0.2)
    # molten gold — Beer-Lambert amber candy pooling where the flow runs deep
    gmetal = _opt_oklch_ramp([(0.97, 0.84, 0.50), (1.00, 0.96, 0.76)], flow)
    goldc = candy_absorb(gmetal, (0.94, 0.60, 0.16), 0.30 + 1.35 * (1.0 - flow), density=1.0)
    g3 = gold[..., None]
    eff = velvet * (1.0 - g3) + goldc * g3
    # whisper of corona in the albedo (the clearcoat carries the real glow)
    halo = (rings * 0.14 - umbra * 0.09)[..., None] * np.array([1.0, 0.85, 0.55], np.float32)
    eff = np.clip(eff + halo, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# ===== FABLE: WOVENLIGHT (FAB_10) ============================================
# Over/under ribbon weave on TWO randomly rotated, domain-warped axes:
# emerald satin warp ribbons crossed by royal-violet MIRROR weft ribbons —
# the weave flips color as the light walks around the car (weft owns the
# mirror flare, warp owns the satin glow). Dive shadows at every crossing
# give the basket its depth; thread striations ride inside each ribbon.
# Three unrelated primary spec geometries: weft visibility checker (M),
# parity-free crossing corridors + threads (R), third-angle sheen pools (Cc).
# ============================================================================
FAB_10 = "fable_wovenlight"


_WOVENLIGHT_FIELDS_CACHE = {}


def _wovenlight_fields(h, w, seed):
    # MEMOIZED (SPB-PERF 2026-06-13): by the Wovenlight ignition doctrine the
    # spec TRACES the paint's exact geometry, so _spec_fable_wovenlight and
    # _paint_fable_wovenlight both request fields for the SAME (h, w, seed) and
    # this ~0.7s build ran TWICE per render. Both callers only READ these arrays
    # (they construct brand-new arrays from them; no in-place mutation — verified
    # 2026-06-13), so replaying a cached result is bit-identical. Measured on a
    # quiet machine: wovenlight paint+spec 2.7s -> 1.9s. FIFO-capped to bound
    # memory. (A blanket fable-wide memo was trialed and reverted — most fable
    # field builders are cheap, so the wrapper/memory overhead wasn't worth it;
    # wovenlight is the one with an expensive enough field build to pay off.)
    key = (int(h), int(w), int(seed))
    hit = _WOVENLIGHT_FIELDS_CACHE.get(key)
    if hit is not None:
        return hit
    out = _wovenlight_fields_compute(h, w, seed)
    _WOVENLIGHT_FIELDS_CACHE[key] = out
    if len(_WOVENLIGHT_FIELDS_CACHE) > 2:
        _WOVENLIGHT_FIELDS_CACHE.pop(next(iter(_WOVENLIGHT_FIELDS_CACHE)))
    return out


def _wovenlight_fields_compute(h, w, seed):
    m = float(max(h, w))
    sr = m / 1024.0
    yy, xx, _, _ = _coords(h, w)
    rng = np.random.default_rng((seed ^ 0x1F2E3D) & 0x7FFFFFFF)
    a1 = rng.uniform(0.0, np.pi)
    a2 = a1 + 0.5 * np.pi + rng.uniform(-0.20, 0.20)
    p1 = max(8.0, rng.uniform(30.0, 40.0) * sr)
    p2 = max(8.0, rng.uniform(34.0, 46.0) * sr)
    # domain warp so the ribbons undulate (no perfectly parallel stripes)
    wu = (_msc(h, w, [max(11, int(41 * sr)), max(29, int(113 * sr))], seed ^ 0x4C5B6A) - 0.5) * (9.0 * sr)
    wv = (_msc(h, w, [max(11, int(47 * sr)), max(29, int(127 * sr))], seed ^ 0x7D8E9F) - 0.5) * (9.0 * sr)
    u = (xx * np.cos(a1) + yy * np.sin(a1) + wu) / p1
    v = (xx * np.cos(a2) + yy * np.sin(a2) + wv) / p2
    iu = np.floor(u)
    iv = np.floor(v)
    fu = (u - iu).astype(np.float32)
    fv = (v - iv).astype(np.float32)
    parity = ((iu + iv) % 2.0).astype(np.float32)            # 1 = weft on top
    warp_top = (1.0 - parity).astype(np.float32)
    # ribbon cross profiles (bright satin center, dipping edges)
    prof_u = np.sin(np.pi * fu).astype(np.float32)
    prof_v = np.sin(np.pi * fv).astype(np.float32)
    # grooves between ribbons (sharp dark seams)
    eu = np.minimum(fu, 1.0 - fu)
    ev = np.minimum(fv, 1.0 - fv)
    groove = (1.0 - np.clip(np.minimum(eu, ev) / 0.055, 0.0, 1.0)).astype(np.float32)
    # dive shadows: the visible ribbon darkens where it slips under its neighbor
    div_u = 1.0 - np.clip(ev / 0.34, 0.0, 1.0)               # warp dives along v
    div_v = 1.0 - np.clip(eu / 0.34, 0.0, 1.0)               # weft dives along u
    dive = (warp_top * div_u + parity * div_v).astype(np.float32)
    # parity-FREE crossing corridor lattice (R's own geometry: every boundary)
    corridor = np.maximum(1.0 - np.clip(eu / 0.30, 0.0, 1.0),
                          1.0 - np.clip(ev / 0.30, 0.0, 1.0)).astype(np.float32)
    # thread striations (each axis its own count — micro band)
    n1 = float(rng.integers(6, 9))
    n2 = float(rng.integers(6, 9))
    th_u = (0.5 + 0.5 * np.cos(2.0 * np.pi * fu * n1)).astype(np.float32)
    th_v = (0.5 + 0.5 * np.cos(2.0 * np.pi * fv * n2)).astype(np.float32)
    thread = (warp_top * th_u + parity * th_v).astype(np.float32)
    # third-angle sheen pools (Cc's own geometry) + macro breath
    a3 = rng.uniform(0.0, np.pi)
    p3 = max(40.0, rng.uniform(150.0, 230.0) * sr)
    w3 = (_msc(h, w, [max(17, int(67 * sr)), max(43, int(171 * sr))], seed ^ 0xA0B1C2) - 0.5) * (38.0 * sr)
    c3 = (xx * np.cos(a3) + yy * np.sin(a3) + w3) / p3
    sheen = ((0.5 + 0.5 * np.sin(2.0 * np.pi * c3)) ** 2.2).astype(np.float32)
    macro = _msc(h, w, [max(31, int(127 * sr)), max(71, int(283 * sr))], seed ^ 0xD3E4F5).astype(np.float32)
    return warp_top, parity, prof_u, prof_v, groove, dive, corridor, thread, sheen, macro


def _spec_fable_wovenlight(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_10, seed)
    (warp_top, parity, prof_u, prof_v, groove, dive,
     corridor, thread, sheen, macro) = _wovenlight_fields(h, w, s)
    g1 = np.random.default_rng((s ^ 0x51CA51) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    # M — PRIMARY: the violet weft checker. Mirror ribbons flare near-max;
    # the emerald warp only carries a soft satin gleam. Grooves kill M.
    M = 26.0 + 206.0 * parity * (0.70 + 0.30 * prof_v) + 34.0 * warp_top * prof_u
    M = M * (1.0 - 0.55 * groove)
    # R — PRIMARY: the parity-free crossing-corridor lattice + thread
    # striations (its own geometry); the weft mirror pull stays a cross-term.
    R = 74.0 + 118.0 * corridor + 42.0 * (thread - 0.5) - 38.0 * parity + 16.0 * (g1 - 0.5)
    # Cc — PRIMARY: third-angle sheen pools wandering across the weave;
    # groove seams drink a little of the wet coat.
    Cc = 58.0 + 168.0 * sheen + 24.0 * (macro - 0.5) - 20.0 * groove
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_wovenlight(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_10, seed)
    (warp_top, parity, prof_u, prof_v, groove, dive,
     corridor, thread, sheen, macro) = _wovenlight_fields(h, w, s)
    # emerald satin warp (OKLab ramp keeps the greens rich end to end)
    t_w = np.clip(0.12 + 0.62 * prof_u + 0.18 * (thread - 0.5) + 0.10 * (macro - 0.5), 0.0, 1.0)
    emerald = _opt_oklch_ramp([(0.012, 0.10, 0.055), (0.030, 0.34, 0.165), (0.30, 0.78, 0.42)],
                         t_w, flatten_lightness=0.15)
    # royal violet mirror weft
    t_f = np.clip(0.10 + 0.64 * prof_v + 0.18 * (thread - 0.5) + 0.10 * (macro - 0.5), 0.0, 1.0)
    violet = _opt_oklch_ramp([(0.085, 0.025, 0.20), (0.30, 0.09, 0.58), (0.66, 0.38, 0.95)],
                        t_f, flatten_lightness=0.15)
    wt = warp_top[..., None]
    eff = emerald * wt + violet * (1.0 - wt)
    # over/under depth: dive shadows + sharp groove seams
    shade = (1.0 - 0.42 * dive) * (1.0 - 0.62 * groove)
    eff = eff * shade[..., None]
    # the third-angle light pools kiss the albedo too (subtle)
    eff = np.clip(eff * (0.92 + 0.16 * sheen[..., None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# ===== FABLE: SOVEREIGN FLIP (FAB_11) ========================================
# THREE-phase perceptual flip: a fine scattered Voronoi 3-coloring (~700
# cells) splits the car into matte-oxblood territory (the diffuse body read),
# mirror-champagne territory (owns the M flare), and glass-deep emerald
# candy territory (owns the Cc glow). Three sun geometries = three different
# cars. Thin cloisonné ink seams trace every territory border. R rides its
# own 3-band micro grain, only re-biased per territory (cross-term).
# Decorrelation-by-construction: M=champagne mask, Cc=emerald mask+relief,
# R=independent grain.
# ============================================================================
FAB_11 = "fable_sovereign_flip"


def _sovereign_flip_fields(h, w, seed):
    m = float(max(h, w))
    sr = m / 1024.0
    # fine three-phase territory map (area-true cell density on any grid)
    cells = max(90, int(round(700.0 * (h * w) / (1024.0 * 1024.0))))
    m0, m1, m2 = tri_partition((h, w), (seed ^ 0x3A5C7E) & 0x7FFFFFFF,
                               cells=cells, soften_px=max(0.8, 1.2 * sr))
    # R's own micro grain (3 strong bands)
    grain = _msc(h, w, [max(2, int(3 * sr)), max(5, int(11 * sr)), max(13, int(31 * sr))],
                 seed ^ 0x9B8A7C).astype(np.float32)
    # champagne flake glitter (sharp micro pins, own seed)
    frng = np.random.default_rng((seed ^ 0x5D6E7F) & 0x7FFFFFFF)
    fl = frng.random((h, w)).astype(np.float32)
    flake = np.clip(cv2.GaussianBlur((fl > 0.986).astype(np.float32),
                                     (0, 0), max(0.5, 0.6 * sr)) * 3.2, 0.0, 1.0)
    # emerald glass relief (mid pooling for the candy + the clearcoat)
    relief = _msc(h, w, [max(5, int(13 * sr)), max(11, int(37 * sr)), max(29, int(101 * sr))],
                  seed ^ 0x2C4D6F).astype(np.float32)
    # macro tone drift + cloisonné border ink (sharp edge band)
    drift = _msc(h, w, [max(43, int(151 * sr)), max(89, int(307 * sr))],
                 seed ^ 0x8F9EAD).astype(np.float32)
    border = np.clip(_edge(m0, 5.0) + _edge(m1, 5.0) + _edge(m2, 5.0), 0.0, 1.0).astype(np.float32)
    return m0, m1, m2, grain, flake, relief, drift, border


def _spec_fable_sovereign_flip(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_11, seed)
    m0, m1, m2, grain, flake, relief, drift, border = _sovereign_flip_fields(h, w, s)
    g1 = np.random.default_rng((s ^ 0x6F00D5) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    # M — PRIMARY: the champagne territory is a mirror; flake pins overdrive
    # it to full flare. Oxblood + emerald stay metal-dead.
    M = 24.0 + 212.0 * m1 * (0.74 + 0.26 * flake) + 10.0 * (g1 - 0.5)
    # R — PRIMARY: its own 3-band micro grain; territories only re-bias it
    # (oxblood matte-high, champagne tightened, emerald mid-wet).
    R = 62.0 + 148.0 * grain + 34.0 * m0 - 30.0 * m1 - 8.0 * m2
    # Cc — PRIMARY: the emerald glass territory; relief pools the wet depth,
    # and the ink seams around emerald cells catch a varnish line.
    Cc = 46.0 + 188.0 * m2 * (0.50 + 0.50 * relief) + 22.0 * (drift - 0.5) + 26.0 * border * m2
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_sovereign_flip(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_11, seed)
    m0, m1, m2, grain, flake, relief, drift, border = _sovereign_flip_fields(h, w, s)
    # oxblood: matte diffuse body, velvet-grained (OKLab keeps the red deep,
    # never browned out)
    ox = _opt_oklch_ramp([(0.140, 0.030, 0.045), (0.300, 0.065, 0.085), (0.460, 0.115, 0.115)],
                    np.clip(0.18 + 0.55 * grain + 0.20 * (drift - 0.5), 0.0, 1.0),
                    flatten_lightness=0.15)
    # champagne: bright warm metal with sharp flake glitter
    ch = _opt_oklch_ramp([(0.520, 0.400, 0.240), (0.800, 0.680, 0.460), (0.990, 0.930, 0.740)],
                    np.clip(0.30 + 0.30 * grain + 0.55 * flake, 0.0, 1.0))
    # emerald: TRUE Beer-Lambert candy — pale green metal drowned under an
    # emerald coat that pools deep where the relief dips
    emetal = _opt_oklch_ramp([(0.62, 0.78, 0.66), (0.88, 0.97, 0.88)], grain)
    em = candy_absorb(emetal, (0.030, 0.420, 0.200), 0.55 + 1.55 * (1.0 - relief), density=1.0)
    eff = ox * m0[..., None] + ch * m1[..., None] + em * m2[..., None]
    eff = eff * (0.90 + 0.20 * drift)[..., None]
    # cloisonné ink seams between territories (sharp edges, stained-glass read)
    eff = np.clip(eff * (1.0 - 0.55 * border[..., None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# ===== FABLE: STATIC BLOOM (FAB_12) ==========================================
# tri_partition showcase at mid scale (~120 cells): every territory gets its
# OWN OKLab hue family AND its own motif — electric-cobalt micro-dot static,
# magenta filament streaks on three random axes, and amber soft blooms.
# Each spec channel reads EXACTLY ONE territory's motif (M=static pins,
# R=filament gloss lanes, Cc=bloom glow) — decorrelation by construction.
# ============================================================================
FAB_12 = "fable_static_bloom"


def _static_bloom_fields(h, w, seed):
    m = float(max(h, w))
    sr = m / 1024.0
    cells = max(24, int(round(120.0 * (h * w) / (1024.0 * 1024.0))))
    m0, m1, m2 = tri_partition((h, w), (seed ^ 0x77E1A2) & 0x7FFFFFFF,
                               cells=cells, soften_px=max(1.5, 3.5 * sr))
    yy, xx, _, _ = _coords(h, w)
    # --- motif 0: micro-dot static (two dot sizes, density drifting mid-band)
    rng0 = np.random.default_rng((seed ^ 0x88F2B3) & 0x7FFFFFFF)
    base = rng0.random((h, w)).astype(np.float32)
    dens = _msc(h, w, [max(17, int(61 * sr)), max(43, int(151 * sr))],
                seed ^ 0x99A3C4).astype(np.float32)
    d_small = (base > (0.984 - 0.014 * dens)).astype(np.float32)
    d_big = cv2.GaussianBlur((rng0.random((h, w)).astype(np.float32) > 0.9965).astype(np.float32),
                             (0, 0), max(0.9, 1.6 * sr))
    dots = np.clip(cv2.GaussianBlur(d_small, (0, 0), max(0.45, 0.7 * sr)) * 2.6 + d_big * 5.0,
                   0.0, 1.0).astype(np.float32)
    # --- motif 1: filament streaks — thin warped ridges on THREE random axes
    rng1 = np.random.default_rng((seed ^ 0xAAB4D5) & 0x7FFFFFFF)
    wpx = (_msc(h, w, [max(7, int(23 * sr)), max(19, int(67 * sr))], seed ^ 0xBBC5E6) - 0.5) * (26.0 * sr)
    fil = np.zeros((h, w), np.float32)
    for _ in range(3):
        ang = rng1.uniform(0.0, np.pi)
        per = max(5.0, rng1.uniform(9.0, 16.0) * sr)
        ph = (xx * np.cos(ang) + yy * np.sin(ang) + wpx * rng1.uniform(0.6, 1.2)) / per
        ridge = 1.0 - np.abs(np.sin(np.pi * ph))
        fil = np.maximum(fil, ridge ** 6)
    fil = fil.astype(np.float32)
    # --- motif 2: soft blooms — scattered breathing gaussians with faint rings
    rng2 = np.random.default_rng((seed ^ 0xCCD6F7) & 0x7FFFFFFF)
    bloom = np.zeros((h, w), np.float32)
    for _ in range(130):
        cy = rng2.uniform(0.0, h)
        cx = rng2.uniform(0.0, w)
        rad = max(4.0, rng2.uniform(0.012, 0.050) * m)
        amp = rng2.uniform(0.4, 1.0)
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, 4.2 * rad)  # tail < 2e-4
        d2 = (yy[y0:y1, x0:x1] - cy) ** 2 + (xx[y0:y1, x0:x1] - cx) ** 2
        g = np.exp(-d2 / (2.0 * rad * rad))
        bloom[y0:y1, x0:x1] += amp * g * (0.75 + 0.25 * np.cos(np.sqrt(d2) / (rad * 0.5)))
    bloom = np.clip(bloom / max(float(np.quantile(bloom, 0.998)), 1e-3), 0.0, 1.0).astype(np.float32)
    return m0, m1, m2, dots, fil, bloom, dens


def _spec_fable_static_bloom(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_12, seed)
    m0, m1, m2, dots, fil, bloom, dens = _static_bloom_fields(h, w, s)
    g1 = np.random.default_rng((s ^ 0x10F0A1) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    g2 = np.random.default_rng((s ^ 0x20E1B2) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    g3 = np.random.default_rng((s ^ 0x30D2C3) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    sr = max(h, w) / 1024.0
    cmac = _msc(h, w, [max(37, int(131 * sr)), max(83, int(293 * sr))],
                s ^ 0x40C3D4).astype(np.float32)
    # M — reads ONLY the static territory: every dot is a mirror pin.
    M = 28.0 + 212.0 * dots * m0 + 12.0 * (g1 - 0.5)
    # R — reads ONLY the filament territory: gloss lanes cut through matte.
    R = 168.0 - 132.0 * fil * m1 + 20.0 * (g2 - 0.5)
    # Cc — reads ONLY the bloom territory: the glow pools in the blooms,
    # with its own slow macro breath everywhere else.
    Cc = 50.0 + 190.0 * bloom * m2 + 18.0 * (cmac - 0.5) + 12.0 * (g3 - 0.5)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_static_bloom(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_12, seed)
    m0, m1, m2, dots, fil, bloom, dens = _static_bloom_fields(h, w, s)
    # territory 0 — electric cobalt static: bright cyan pins on deep blue
    col0 = _opt_oklch_ramp([(0.030, 0.070, 0.220), (0.070, 0.220, 0.500), (0.350, 0.850, 1.000)],
                      np.clip(0.16 + 0.62 * dots + 0.22 * (dens - 0.5), 0.0, 1.0),
                      flatten_lightness=0.1)
    # territory 1 — magenta filaments burning through dark plum
    col1 = _opt_oklch_ramp([(0.160, 0.030, 0.140), (0.450, 0.080, 0.420), (0.950, 0.450, 0.850)],
                      np.clip(0.14 + 0.74 * fil, 0.0, 1.0), flatten_lightness=0.1)
    # territory 2 — amber blooms glowing out of deep maroon
    col2 = _opt_oklch_ramp([(0.200, 0.060, 0.040), (0.650, 0.280, 0.100), (1.000, 0.750, 0.400)],
                      np.clip(0.12 + 0.80 * bloom, 0.0, 1.0), flatten_lightness=0.1)
    eff = col0 * m0[..., None] + col1 * m1[..., None] + col2 * m2[..., None]
    eff = np.clip(eff * (0.92 + 0.16 * dens)[..., None], 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE #13 — AURORA TRAVEL (fable_aurora_travel)
# HUE-TRAVEL RAMP: a flowing multi-axis aurora-curtain field carries an OKLCH
# teal→violet→magenta ramp (flattened lightness — no muddy midpoints) while
# the ROUGHNESS map cuts glossy corridors ANTI-PARALLEL to the curtain axes:
# the live highlight rides the corridors and physically migrates ACROSS hues
# as the car rotates. M flares the curtain-edge filaments; Cc pools shimmer
# in its own scattered ponds. UV-agnostic: 4 random curtain axes + isotropic
# domain warp, corridors on their own jittered crossing axes, pools scattered
# at random centers — no global up/down anywhere.
# ============================================================================
FAB_13 = "fable_aurora_travel"


def _aurora_travel_fields(h, w, seed):
    """flow (hue key), filaments (M), corridors (R), pools (Cc) — HxW [0,1]."""
    m = float(max(h, w))
    yy, xx, _, _ = _coords(h, w)

    # flow: 4 random-axis warped sine curtains (macro band) + mid ripple
    rng_f = np.random.default_rng(seed ^ 0x13A001)
    axes = [float(rng_f.uniform(0.0, np.pi)) for _ in range(4)]
    warp = _msc(h, w, [max(int(m * 0.015), 3), max(int(m * 0.06), 7), max(int(m * 0.16), 11)],
                seed ^ 0x13B002) - 0.5
    flow = np.zeros((h, w), np.float32)
    for ang in axes:
        u = (float(np.cos(ang)) * xx + float(np.sin(ang)) * yy) / m
        lam = float(rng_f.uniform(5.0, 10.0))
        ph = float(rng_f.uniform(0.0, 2.0 * np.pi))
        amp = float(rng_f.uniform(0.6, 1.1))
        flow += amp * np.sin(2.0 * np.pi * lam * (u + 0.17 * warp) + ph)
    flow -= flow.min()
    flow /= max(float(flow.max()), 1e-6)
    ripple = _msc(h, w, [max(int(m * 0.03), 4), max(int(m * 0.09), 8)], seed ^ 0x13C003)
    flow = np.clip(0.82 * flow + 0.18 * ripple, 0.0, 1.0).astype(np.float32)

    # filaments: sharpened curtain edges + own micro streamers (M primary)
    fil = _edge(flow, gain=m * 0.030)
    fil = np.clip(fil ** 1.5 * 1.9, 0.0, 1.0)
    streamers = _msc(h, w, [2, max(int(m * 0.006), 3), max(int(m * 0.018), 5)], seed ^ 0x13D004)
    fil = np.clip(fil * (0.55 + 0.45 * streamers) + 0.30 * (streamers > 0.90), 0.0, 1.0).astype(np.float32)

    # corridors: glossy lanes ANTI-PARALLEL (crossing) the curtain axes — own
    # wavelengths/phases/warp/jitter = R's own primary geometry
    rng_r = np.random.default_rng(seed ^ 0x13E005)
    warp_r = _msc(h, w, [max(int(m * 0.025), 4), max(int(m * 0.10), 9)], seed ^ 0x13F006) - 0.5
    lanes = np.zeros((h, w), np.float32)
    for k in range(3):
        ang = axes[k] + 0.5 * np.pi + float(rng_r.uniform(-0.35, 0.35))
        u = (float(np.cos(ang)) * xx + float(np.sin(ang)) * yy) / m
        lam = float(rng_r.uniform(2.5, 6.0))
        ph = float(rng_r.uniform(0.0, 2.0 * np.pi))
        sv = 0.5 + 0.5 * np.sin(2.0 * np.pi * lam * (u + 0.24 * warp_r) + ph)
        lane = np.clip((sv - 0.70) / 0.11, 0.0, 1.0)
        lanes = np.maximum(lanes, (lane * lane * (3.0 - 2.0 * lane)).astype(np.float32))

    # pools: scattered shimmer ponds + slow drift (Cc primary)
    def _aurora_travel_pond(acc, yy2, xx2, cy, cx, rad, ang2, amp):
        rr = max(2.4 * rad, 2.0)
        d2 = (yy2 - cy) ** 2 + (xx2 - cx) ** 2
        acc += amp * np.exp(-d2 / (2.0 * rr * rr))

    pools = _opt_scatter_field(h, w, seed ^ 0x130907, 64, _aurora_travel_pond,
                               lambda rad: 3.6 * max(2.4 * rad, 2.0))
    pools /= max(float(pools.max()), 1e-6)
    drift = _msc(h, w, [max(int(m * 0.12), 9), max(int(m * 0.30), 17)], seed ^ 0x131A08)
    pools = np.clip(0.62 * pools + 0.38 * drift, 0.0, 1.0).astype(np.float32)
    return flow, fil, lanes, pools


def _spec_fable_aurora_travel(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_13, seed)
    flow, fil, lanes, pools = _aurora_travel_fields(h, w, s)
    m = float(max(h, w))
    micro_m = _msc(h, w, [2, max(int(m * 0.006), 3)], s ^ 0x13AB10)
    micro_r = _msc(h, w, [3, max(int(m * 0.009), 4)], s ^ 0x13BC11)
    micro_c = _msc(h, w, [2, max(int(m * 0.005), 3)], s ^ 0x13CD12)
    # M: curtain filaments flare; faint flow backlight stays a small cross-term
    M = 24.0 + 192.0 * fil + 24.0 * micro_m + 16.0 * flow
    # R: mirror corridors cut ACROSS the hue bands (low R = tight highlight lanes)
    R = 180.0 - 140.0 * lanes + 26.0 * micro_r - 10.0 * fil
    # Cc: shimmer ponds glow wet + micro pin sparkle
    Cc = 56.0 + 160.0 * pools + 24.0 * (micro_c > 0.88).astype(np.float32) + 10.0 * micro_c
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_aurora_travel(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_13, seed)
    flow, fil, lanes, pools = _aurora_travel_fields(h, w, s)
    m = float(max(h, w))
    # OKLCH hue-travel ramp: teal → violet → magenta at even perceived lightness
    stops = [(0.03, 0.60, 0.56), (0.30, 0.16, 0.66), (0.78, 0.12, 0.54)]
    eff = _opt_oklch_ramp(stops, flow, flatten_lightness=0.6)
    lin = srgb_to_linear(eff)
    lin = lin + (fil ** 1.3)[:, :, None] * np.array([0.28, 0.42, 0.50], np.float32)
    lin = lin * (1.0 - 0.22 * pools[:, :, None])  # ponds deepen into night
    eff = linear_to_srgb(np.clip(lin, 0.0, 1.0))
    grain = _msc(h, w, [2, max(int(m * 0.005), 3)], s ^ 0x13DE13)
    eff = np.clip(eff * (0.93 + 0.12 * grain[:, :, None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE #14 — SAFFRON CIRCUIT (fable_saffron_circuit)
# Etched micro-circuit relief: ~230 trace segments with elbow bends + 140 via
# dots scattered at MANY random angles (never one grid). Paint = flat-light
# OKLCH saffron→rose→ember ramp keyed to LOCAL TRACE DENSITY, with the clear
# pooling dark candy (Beer–Lambert) inside the grooves. Spec: R = inverse
# etch depth (grooves run glossy), M = trace-edge glints + solder sparks,
# Cc = via-dot glow at its OWN scattered points. UV-agnostic: every trace and
# via has its own random position/angle; density is an isotropic blur.
# ============================================================================
FAB_14 = "fable_saffron_circuit"


def _saffron_circuit_fields(h, w, seed):
    """etch (R), density (paint key), glints (M), viaglow (Cc) — HxW [0,1]."""
    m = float(max(h, w))
    rng_t = np.random.default_rng(seed ^ 0x14A001)
    ink8 = np.zeros((h, w), np.uint8)
    for _ in range(230):  # scatter placement loop
        x0 = float(rng_t.uniform(0, w))
        y0 = float(rng_t.uniform(0, h))
        ang = float(rng_t.uniform(0.0, 2.0 * np.pi))
        ln = float(rng_t.uniform(0.030, 0.125)) * m
        th = max(2, int(round(float(rng_t.uniform(0.0022, 0.0050)) * m)))
        x1 = x0 + float(np.cos(ang)) * ln
        y1 = y0 + float(np.sin(ang)) * ln
        cv2.line(ink8, (int(x0), int(y0)), (int(x1), int(y1)), 255, th, cv2.LINE_AA)
        if rng_t.random() < 0.6:  # elbow bend in the trace's own frame
            bend = ang + float(rng_t.choice((-1.0, 1.0))) * float(rng_t.choice((np.pi / 4.0, np.pi / 2.0)))
            l2 = float(rng_t.uniform(0.020, 0.085)) * m
            x2 = x1 + float(np.cos(bend)) * l2
            y2 = y1 + float(np.sin(bend)) * l2
            cv2.line(ink8, (int(x1), int(y1)), (int(x2), int(y2)), 255, th, cv2.LINE_AA)
    ink = ink8.astype(np.float32) / 255.0

    # groove relief with its own slow depth modulation (R primary)
    depth_mod = _msc(h, w, [max(int(m * 0.07), 7), max(int(m * 0.20), 13)], seed ^ 0x14B002)
    etch = cv2.GaussianBlur(ink, (0, 0), max(0.6, m * 0.0009))
    etch = np.clip(etch * (0.55 + 0.45 * depth_mod), 0.0, 1.0).astype(np.float32)

    # local trace density (isotropic macro band — keys the hue ramp).
    # Quantile stretch so the ramp truly reaches saffron AND ember ends.
    density = cv2.GaussianBlur(ink, (0, 0), m * 0.032)
    d_lo = float(np.quantile(density, 0.05))
    d_hi = float(np.quantile(density, 0.95))
    density = np.clip((density - d_lo) / max(d_hi - d_lo, 1e-6), 0.0, 1.0).astype(np.float32)

    # trace-edge glints + own solder sparks (M primary)
    glints = _edge(etch, gain=m * 0.02)
    sparks = _msc(h, w, [2, max(int(m * 0.005), 3)], seed ^ 0x14C003)
    glints = np.clip(glints * (0.60 + 0.40 * sparks) + 0.50 * (sparks > 0.93), 0.0, 1.0).astype(np.float32)

    # via dots at their OWN scattered points (Cc primary)
    rng_v = np.random.default_rng(seed ^ 0x14D004)
    via8 = np.zeros((h, w), np.uint8)
    for _ in range(140):  # scatter placement loop
        cx = int(rng_v.uniform(0, w))
        cy = int(rng_v.uniform(0, h))
        rr = max(2, int(round(float(rng_v.uniform(0.0025, 0.0065)) * m)))
        cv2.circle(via8, (cx, cy), rr, 255, -1, cv2.LINE_AA)
    via = via8.astype(np.float32) / 255.0
    halo = cv2.GaussianBlur(via, (0, 0), m * 0.009)
    halo /= max(float(halo.max()), 1e-6)
    slow_c = _msc(h, w, [max(int(m * 0.10), 9), max(int(m * 0.26), 15)], seed ^ 0x14E005)
    viaglow = np.clip(0.55 * halo + 0.30 * via + 0.25 * slow_c, 0.0, 1.0).astype(np.float32)
    return etch, density, glints, viaglow


def _spec_fable_saffron_circuit(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_14, seed)
    etch, density, glints, viaglow = _saffron_circuit_fields(h, w, s)
    m = float(max(h, w))
    micro_m = _msc(h, w, [2, max(int(m * 0.006), 3)], s ^ 0x14F006)
    micro_r = _msc(h, w, [3, max(int(m * 0.010), 4)], s ^ 0x140A07)
    micro_c = _msc(h, w, [2, max(int(m * 0.005), 3)], s ^ 0x141B08)
    # M: copper-edge glints flare under direct light
    M = 22.0 + 198.0 * glints + 22.0 * micro_m + 14.0 * density
    # R: INVERSE etch depth — grooves polish glossy, the plateau runs satin
    R = 196.0 - 168.0 * etch + 26.0 * micro_r - 12.0 * density
    # Cc: via-dot glow pools the wet clear at its own scattered points
    Cc = 48.0 + 178.0 * viaglow + 16.0 * (micro_c > 0.90).astype(np.float32) + 8.0 * micro_c
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_saffron_circuit(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_14, seed)
    etch, density, glints, viaglow = _saffron_circuit_fields(h, w, s)
    m = float(max(h, w))
    # flat-lightness OKLCH ramp keyed to local circuit density
    stops = [(0.99, 0.66, 0.14), (0.88, 0.34, 0.36), (0.46, 0.14, 0.10)]
    drift = _msc(h, w, [max(int(m * 0.05), 5), max(int(m * 0.14), 9)], s ^ 0x142C09)
    t = np.clip(0.85 * density + 0.15 * drift, 0.0, 1.0)
    eff = _opt_oklch_ramp(stops, t, flatten_lightness=0.65)
    # Beer–Lambert: the clear pools dark saffron-ember inside the etched grooves
    eff = candy_absorb(eff, (0.62, 0.27, 0.08), etch * 1.5, density=1.1)
    lin = srgb_to_linear(eff)
    lin = lin + (glints ** 1.2)[:, :, None] * np.array([0.50, 0.34, 0.10], np.float32)
    lin = lin + (viaglow ** 2.0)[:, :, None] * np.array([0.10, 0.03, 0.006], np.float32)
    eff = linear_to_srgb(np.clip(lin, 0.0, 1.0))
    grain = _msc(h, w, [2, max(int(m * 0.004), 2)], s ^ 0x143D0A)
    eff = np.clip(eff * (0.94 + 0.10 * grain[:, :, None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE #15 — QUICKSILVER GARDEN (fable_quicksilver_garden)
# Liquid chrome overgrown with ~120 organic mottle cells (domain-warped
# Voronoi). Each cell grows its OWN OKLab pastel mini-ramp at its OWN random
# orientation (Beer–Lambert pastel candy over the chrome) behind a mirror-
# bright rim. R is a PER-CELL random — different cells flare at different
# angles, so the garden shimmers cell-by-cell as the car drives. UV-agnostic:
# scattered warped cells, per-cell random ramp directions; nothing global.
# ============================================================================
FAB_15 = "fable_quicksilver_garden"


def _quicksilver_garden_fields(h, w, seed):
    """(tcell, interior, rim, core, owner, n) — warped-Voronoi cell geometry.
    tcell    : per-pixel master-ramp coordinate (per-cell window + orientation)
    interior : soft cell-interior mask (0 at borders)
    rim      : thin mirror rim network
    core     : radial pooling toward each cell's own center
    owner    : int32 owning-cell index map (per-cell random lookups)
    """
    m = float(max(h, w))
    yy, xx, _, _ = _coords(h, w)
    n = 120
    rng = np.random.default_rng(seed ^ 0x15A001)
    py = rng.uniform(0, h, n).astype(np.float32)
    px = rng.uniform(0, w, n).astype(np.float32)
    cang = rng.uniform(0.0, 2.0 * np.pi, n).astype(np.float32)
    crad = (np.sqrt(h * w / float(n)) * rng.uniform(0.70, 1.25, n)).astype(np.float32)
    toff = rng.uniform(0.0, 0.58, n).astype(np.float32)

    wy = (_msc(h, w, [max(int(m * 0.02), 3), max(int(m * 0.08), 7)], seed ^ 0x15B002) - 0.5) * (m * 0.060)
    wx = (_msc(h, w, [max(int(m * 0.02), 3), max(int(m * 0.08), 7)], seed ^ 0x15C003) - 0.5) * (m * 0.060)
    yyw = yy + wy
    xxw = xx + wx

    d1, d2, owner = _opt_voro_top2(yyw, xxw, py, px)  # bit-identical to loop
    d1 = np.sqrt(d1)
    d2 = np.sqrt(d2)
    border = d2 - d1
    rimw = max(m * 0.004, 1.5)
    rim = np.exp(-((border / rimw) ** 2)).astype(np.float32)
    interior = np.clip(border / (m * 0.045), 0.0, 1.0)
    interior = (interior * interior * (3.0 - 2.0 * interior)).astype(np.float32)

    cxm = px[owner]
    cym = py[owner]
    am = cang[owner]
    rm = np.maximum(crad[owner], 1.0)
    proj = ((xxw - cxm) * np.cos(am) + (yyw - cym) * np.sin(am)) / rm
    tcell = np.clip(toff[owner] + 0.42 * np.clip(0.5 + 0.5 * proj, 0.0, 1.0), 0.0, 1.0).astype(np.float32)
    core = np.clip(1.0 - d1 / rm, 0.0, 1.0).astype(np.float32)
    return tcell, interior, rim, core, owner, n


def _spec_fable_quicksilver_garden(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_15, seed)
    tcell, interior, rim, core, owner, n = _quicksilver_garden_fields(h, w, s)
    m = float(max(h, w))
    rng = np.random.default_rng(s ^ 0x15D004)
    rcell = rng.uniform(34.0, 212.0, n).astype(np.float32)  # per-cell flare angle
    ccamp = rng.uniform(0.40, 1.00, n).astype(np.float32)   # per-cell pool depth
    micro_r = _msc(h, w, [3, max(int(m * 0.008), 3)], s ^ 0x15E005)
    micro_m = _msc(h, w, [2, max(int(m * 0.005), 3)], s ^ 0x15F006)
    slow_c = _msc(h, w, [max(int(m * 0.11), 9), max(int(m * 0.28), 15)], s ^ 0x150A07)
    # R: every cell rolls its OWN roughness — the garden flares cell-by-cell
    R = rcell[owner] * (0.88 + 0.24 * micro_r)
    # M: mirror rim network + quicksilver spark pins
    M = 26.0 + 212.0 * (rim ** 0.9) + 30.0 * (micro_m > 0.90).astype(np.float32) + 12.0 * micro_m
    # Cc: wet pooling toward each cell's own center, per-cell depth + slow drift
    Cc = 44.0 + 168.0 * (core ** 1.5) * ccamp[owner] + 28.0 * slow_c
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_quicksilver_garden(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_15, seed)
    tcell, interior, rim, core, owner, n = _quicksilver_garden_fields(h, w, s)
    m = float(max(h, w))
    # liquid chrome bed: bright omnidirectional streak luminance + hot caustics
    cf = _msc(h, w, [max(int(m * 0.02), 3), max(int(m * 0.07), 6), max(int(m * 0.18), 11)], s ^ 0x151B08)
    cl = 0.32 + 0.60 * cf ** 1.4 + 0.55 * np.clip((cf - 0.80) / 0.10, 0.0, 1.0)
    chrome = np.clip(cl[:, :, None] * np.array([0.94, 0.985, 1.05], np.float32), 0.0, 1.0)
    # per-cell pastel mini-ramps: each cell samples its own window of the master
    # ramp along its own random orientation
    stops = [(0.58, 0.93, 0.78), (0.55, 0.78, 0.96), (0.78, 0.62, 0.93),
             (0.96, 0.62, 0.72), (0.98, 0.88, 0.55)]
    pastel = _opt_oklch_ramp(stops, tcell, flatten_lightness=0.55, exact_edges=True)
    # Beer–Lambert pastel candy over the chrome — pools gently mid-cell so the
    # garden stays PASTEL-lit (not jewel-dark)
    depth = (interior * (0.40 + 0.55 * core)).astype(np.float32)
    eff = candy_absorb(chrome, pastel, depth, density=1.0)
    # mirror-bright rims
    riml = ((rim ** 1.1) * 0.88)[:, :, None]
    eff = eff * (1.0 - riml) + np.array([0.97, 0.985, 1.0], np.float32) * riml
    grain = _msc(h, w, [2, max(int(m * 0.004), 2)], s ^ 0x152C09)
    eff = np.clip(eff * (0.94 + 0.11 * grain[:, :, None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE #16 — EMBERLINE DRIFT (fable_emberline_drift)
# Dune-wave interference FOLDED from 4 random axes into a cusped ridge
# lattice; the OKLab gold→crimson→smoke ramp rides the dune value. Sheen
# corridors (low-R lanes) cross the dunes on their OWN random axes; M glints
# only the dune crests; Cc pools ember glow in its OWN slow field with the
# dune-valley gate held to a small cross-term. UV-agnostic: all axes random
# per seed, folding is symmetric, pooling is isotropic — no global direction.
# ============================================================================
FAB_16 = "fable_emberline_drift"


def _emberline_drift_fields(h, w, seed):
    """dunes (hue key), crest (M), lanes (R), pool (Cc) — HxW [0,1]."""
    m = float(max(h, w))
    yy, xx, _, _ = _coords(h, w)
    rng_d = np.random.default_rng(seed ^ 0x16A001)
    warp = _msc(h, w, [max(int(m * 0.02), 3), max(int(m * 0.07), 6), max(int(m * 0.18), 11)],
                seed ^ 0x16B002) - 0.5
    acc = np.zeros((h, w), np.float32)
    wsum = 0.0
    for _ in range(4):
        ang = float(rng_d.uniform(0.0, np.pi))
        u = (float(np.cos(ang)) * xx + float(np.sin(ang)) * yy) / m
        lam = float(rng_d.uniform(4.0, 9.0))
        ph = float(rng_d.uniform(0.0, 2.0 * np.pi))
        wgt = float(rng_d.uniform(0.6, 1.1))
        folded = np.abs(np.sin(2.0 * np.pi * lam * (u + 0.20 * warp) + ph)).astype(np.float32)
        acc += wgt * (1.0 - folded ** 0.7)  # cusped dune ridges, not smooth sines
        wsum += wgt
    dunes = acc / max(wsum, 1e-6)
    # quantile contrast stretch: the 4-wave folded sum central-limits toward
    # the middle — stretch it so gold ridges AND smoke valleys both exist
    q_lo = float(np.quantile(dunes, 0.07))
    q_hi = float(np.quantile(dunes, 0.93))
    dunes = np.clip((dunes - q_lo) / max(q_hi - q_lo, 1e-6), 0.0, 1.0)
    mottle = _msc(h, w, [max(int(m * 0.04), 4), max(int(m * 0.11), 8)], seed ^ 0x16C003)
    dunes = np.clip(0.82 * dunes + 0.18 * mottle, 0.0, 1.0).astype(np.float32)

    # crest glints: thin caps above the high quantile (M primary)
    q1 = float(np.quantile(dunes, 0.86))
    q2 = float(np.quantile(dunes, 0.985))
    crest = np.clip((dunes - q1) / max(q2 - q1, 1e-5), 0.0, 1.0) ** 1.4
    specks = _msc(h, w, [2, max(int(m * 0.006), 3)], seed ^ 0x16D004)
    crest = np.clip(crest * (0.60 + 0.40 * specks) + 0.35 * (specks > 0.93), 0.0, 1.0).astype(np.float32)

    # sheen corridors on their OWN axes (R primary)
    rng_r = np.random.default_rng(seed ^ 0x16E005)
    warp_r = _msc(h, w, [max(int(m * 0.03), 4), max(int(m * 0.12), 9)], seed ^ 0x16F006) - 0.5
    lanes = np.zeros((h, w), np.float32)
    for _ in range(3):
        ang = float(rng_r.uniform(0.0, np.pi))
        u = (float(np.cos(ang)) * xx + float(np.sin(ang)) * yy) / m
        lam = float(rng_r.uniform(2.0, 5.0))
        ph = float(rng_r.uniform(0.0, 2.0 * np.pi))
        sv = 0.5 + 0.5 * np.sin(2.0 * np.pi * lam * (u + 0.27 * warp_r) + ph)
        lane = np.clip((sv - 0.66) / 0.14, 0.0, 1.0)
        lanes = np.maximum(lanes, (lane * lane * (3.0 - 2.0 * lane)).astype(np.float32))

    # ember pooling: OWN slow field, valley-gated as a small cross-term (Cc)
    slow = _msc(h, w, [max(int(m * 0.09), 8), max(int(m * 0.24), 13), max(int(m * 0.45), 21)],
                seed ^ 0x160A07)
    pool = np.clip(0.78 * slow + 0.22 * (1.0 - dunes), 0.0, 1.0).astype(np.float32)
    return dunes, crest, lanes, pool


def _spec_fable_emberline_drift(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_16, seed)
    dunes, crest, lanes, pool = _emberline_drift_fields(h, w, s)
    m = float(max(h, w))
    micro_m = _msc(h, w, [2, max(int(m * 0.006), 3)], s ^ 0x161B08)
    micro_r = _msc(h, w, [3, max(int(m * 0.009), 4)], s ^ 0x162C09)
    micro_c = _msc(h, w, [2, max(int(m * 0.005), 3)], s ^ 0x163D0A)
    # M: only the dune crests catch metal glint
    M = 24.0 + 204.0 * crest + 22.0 * micro_m
    # R: wide sheen corridors cross the dunes at their own angles
    R = 186.0 - 132.0 * lanes + 24.0 * micro_r
    # Cc: ember glow pools in its own slow drift (valley gate stays small)
    Cc = 52.0 + 158.0 * pool + 22.0 * (micro_c > 0.89).astype(np.float32) + 10.0 * micro_c
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_emberline_drift(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_16, seed)
    dunes, crest, lanes, pool = _emberline_drift_fields(h, w, s)
    m = float(max(h, w))
    # OKLab ramp: gold → crimson → smoke. The dune value carries the detail and
    # a slow isotropic drift opens MACRO hue zones (gold fields vs smoke fields)
    # so the ramp survives track distance — no global axis, just slow noise.
    drift_t = _msc(h, w, [max(int(m * 0.13), 9), max(int(m * 0.34), 17)], s ^ 0x165F0C)
    tkey = np.clip(0.58 * dunes + 0.42 * drift_t, 0.0, 1.0)
    stops = [(0.96, 0.74, 0.20), (0.74, 0.13, 0.10), (0.30, 0.27, 0.29)]
    eff = _opt_oklch_ramp(stops, tkey, flatten_lightness=0.5)
    lin = srgb_to_linear(eff)
    lin = lin + (crest ** 1.2)[:, :, None] * np.array([0.55, 0.36, 0.10], np.float32)
    lin = lin + (pool ** 1.8)[:, :, None] * np.array([0.22, 0.05, 0.01], np.float32)
    eff = linear_to_srgb(np.clip(lin, 0.0, 1.0))
    grain = _msc(h, w, [2, max(int(m * 0.005), 3)], s ^ 0x164E0B)
    eff = np.clip(eff * (0.93 + 0.12 * grain[:, :, None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE 17) DUOMORPH — dual-artwork angle choreography. Artwork A (orbital
# glyph rosettes) lives in METALLIC and FLARES under direct sun; artwork B
# (counter-flowing ribbon arcs) lives in CLEARCOAT and glows at wet glancing
# angles; roughness rides its own neutral grain so the two shows never blur.
# Deep graphite paint whispers BOTH artworks at low contrast — turn the car
# and the sun decides which drawing you see.
# ============================================================================
FAB_17 = "fable_duomorph"


def _duomorph_rosettes(h, w, seed):
    """Artwork A: scattered orbital glyph rosettes — three concentric ring
    lines + an orbit-dot comb + a hot core, every instance at its own random
    center and rotation (UV-orientation-agnostic by construction)."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    px = m / 1024.0
    acc = np.zeros((h, w), np.float32)
    for _ in range(26):
        cy = float(rng.uniform(0.0, h))
        cx = float(rng.uniform(0.0, w))
        rot = float(rng.uniform(0.0, 2.0 * np.pi))
        r0 = float(rng.uniform(0.042, 0.088)) * m
        lw = max(float(rng.uniform(2.2, 3.4)) * px, 1.1)
        amp = float(rng.uniform(0.62, 1.0))
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, r0 + 12.0 * lw)  # ring tails ~0
        dy = yy[y0:y1, x0:x1] - cy
        dx = xx[y0:y1, x0:x1] - cx
        r = np.sqrt(dy * dy + dx * dx) + 1e-6
        th = np.arctan2(dy, dx)
        glyph = np.zeros_like(r)
        for fr in (0.42, 0.72, 1.0):
            np.maximum(glyph, np.exp(-((r - r0 * fr) / lw) ** 2), out=glyph)
        nd = int(rng.integers(5, 10))
        comb = np.clip(np.cos(nd * (th - rot)), 0.0, 1.0) ** 16
        orbit = np.exp(-((r - r0 * 0.72) / (lw * 2.6)) ** 2)
        np.maximum(glyph, comb * orbit, out=glyph)
        np.maximum(glyph, np.exp(-(r / (2.8 * px)) ** 2), out=glyph)
        sub = acc[y0:y1, x0:x1]
        np.maximum(sub, glyph * amp, out=sub)
    return np.clip(acc, 0.0, 1.0).astype(np.float32)


def _duomorph_arcs(h, w, seed):
    """Artwork B: counter-flowing ribbon arcs — long sweeping circle segments
    around their OWN scattered (often off-canvas) centers; every arc gets its
    own radius, angular span and rotation, so no two flow the same way."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    px = m / 1024.0
    acc = np.zeros((h, w), np.float32)
    for _ in range(18):
        cy = float(rng.uniform(-0.35, 1.35)) * h
        cx = float(rng.uniform(-0.35, 1.35)) * w
        rg = float(rng.uniform(0.20, 0.62)) * m
        rot = float(rng.uniform(0.0, 2.0 * np.pi))
        span = float(rng.uniform(0.40, 1.10))
        wd = max(float(rng.uniform(2.4, 6.0)) * px, 1.2)
        amp = float(rng.uniform(0.55, 1.0))
        y0, y1, x0, x1 = _opt_arc_bbox(h, w, cy, cx, max(rg - 4.5 * wd, 0.0),
                                       rg + 4.5 * wd, rot, 2.6 * span)
        if y0 >= y1 or x0 >= x1:
            continue
        dy = yy[y0:y1, x0:x1] - cy
        dx = xx[y0:y1, x0:x1] - cx
        r = np.sqrt(dy * dy + dx * dx) + 1e-6
        th = np.arctan2(dy, dx)
        d = np.mod(th - rot + np.pi, 2.0 * np.pi) - np.pi
        ribbon = np.exp(-((r - rg) / wd) ** 2) * np.exp(-(d / span) ** 2)
        sub = acc[y0:y1, x0:x1]
        np.maximum(sub, ribbon * amp, out=sub)
    return np.clip(acc, 0.0, 1.0).astype(np.float32)


def _duomorph_fields(h, w, seed):
    rosette = _duomorph_rosettes(h, w, seed ^ 0x17A1)
    arcs = _duomorph_arcs(h, w, seed ^ 0x17B2)
    grain = _msc(h, w, [2, 5, 12], seed ^ 0x17C3)
    macro = _msc(h, w, [46, 110, 230], seed ^ 0x17D4)
    return rosette, arcs, grain, macro


def _spec_fable_duomorph(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_17, seed)
    rosette, arcs, grain, _macro = _duomorph_fields(h, w, s)
    glint = _msc(h, w, [2, 4], s ^ 0x17E5)
    rough_macro = _msc(h, w, [40, 95, 210], s ^ 0x17F6)
    glow = _msc(h, w, [70, 160], s ^ 0x1707)
    # ANGLE CHOREOGRAPHY: M owns artwork A (rosettes), Cc owns artwork B
    # (ribbon arcs), R owns a neutral grain+macro story — three separate shows.
    M = 26.0 + rosette * 212.0 + glint * 18.0
    R = 150.0 + (grain - 0.5) * 96.0 - rough_macro * 52.0
    Cc = 30.0 + arcs * 198.0 + glow * 26.0
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_duomorph(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_17, seed)
    rosette, arcs, grain, macro = _duomorph_fields(h, w, s)
    base = _opt_oklch_ramp([(0.054, 0.058, 0.072), (0.112, 0.116, 0.134)], macro,
                      flatten_lightness=0.25)
    base = base + (grain[:, :, None] - 0.5) * 0.034
    eff = (base
           + rosette[:, :, None] * np.array([0.30, 0.36, 0.46], np.float32) * 0.17
           + arcs[:, :, None] * np.array([0.44, 0.35, 0.21], np.float32) * 0.17)
    eff = np.clip(eff, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE 18) NIGHTBLOOM — dusk indigo→plum OKLab ramp travelling OUTWARD from
# scattered night-sky anchors. Luminous flower-burst petal fans live ALMOST
# ONLY in the clearcoat (a faint hint in the paint), so the car literally
# blooms when low sun pools in the clear. Metallic carries its own scattered
# pollen micro-stars; roughness rides an independent dusk haze.
# ============================================================================
FAB_18 = "fable_nightbloom"


def _nightbloom_pollen_splat(acc, yy, xx, cy, cx, rad, ang, amp):
    """Micro pollen star for the metallic channel: tight 2-6 px twinkle."""
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) + 1e-6
    er = max(rad * 0.14, 1.4)
    local = np.clip(1.0 - r / (er * 2.4), 0.0, 1.0)
    np.maximum(acc, (local ** 2.2) * amp, out=acc)


def _nightbloom_dusk(h, w, seed):
    """Radial-from-scattered-centers dusk carrier in [0,1]: the color ramp
    travels OUTWARD from random anchor points — never top-to-bottom."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    glow = np.zeros((h, w), np.float32)
    for _ in range(7):
        cy = float(rng.uniform(0.0, h))
        cx = float(rng.uniform(0.0, w))
        reach = float(rng.uniform(0.28, 0.52)) * m
        amp = float(rng.uniform(0.65, 1.0))
        r2 = (yy - cy) ** 2 + (xx - cx) ** 2
        glow += np.exp(-r2 / (2.0 * reach * reach)) * amp
    glow /= max(float(glow.max()), 1e-6)
    return glow.astype(np.float32)


def _nightbloom_blooms(h, w, seed):
    """Flower-burst petal fans at random centers + rotations: sharp petal comb
    * annular body * fine radial ribs + a hot pistil core."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    px = m / 1024.0
    acc = np.zeros((h, w), np.float32)
    for _ in range(15):
        cy = float(rng.uniform(0.0, h))
        cx = float(rng.uniform(0.0, w))
        rot = float(rng.uniform(0.0, 2.0 * np.pi))
        rb = float(rng.uniform(0.055, 0.115)) * m
        npet = int(rng.integers(5, 9))
        amp = float(rng.uniform(0.6, 1.0))
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, rb * 1.6)  # body tail < 1e-5
        dy = yy[y0:y1, x0:x1] - cy
        dx = xx[y0:y1, x0:x1] - cx
        r = np.sqrt(dy * dy + dx * dx) + 1e-6
        th = np.arctan2(dy, dx)
        petal = np.clip(np.cos(npet * (th - rot)), 0.0, 1.0) ** 6
        body = np.exp(-((r - rb * 0.52) / (rb * 0.30)) ** 2)
        ribs = 0.5 + 0.5 * np.cos(r / max(3.2 * px, 1.4) * np.pi)
        core = np.exp(-(r / (rb * 0.16)) ** 2)
        sub = acc[y0:y1, x0:x1]
        np.maximum(sub, (petal * body * (0.55 + 0.45 * ribs) + core) * amp, out=sub)
    return np.clip(acc, 0.0, 1.0).astype(np.float32)


def _nightbloom_fields(h, w, seed):
    dusk = _nightbloom_dusk(h, w, seed ^ 0x18A1)
    bloom = _nightbloom_blooms(h, w, seed ^ 0x18B2)
    pollen = _opt_scatter_field(h, w, seed ^ 0x18C3, 430, _nightbloom_pollen_splat,
                                lambda rad: max(rad * 0.14, 1.4) * 2.4 + 1.0)
    haze = _msc(h, w, [34, 80, 190], seed ^ 0x18D4)
    return dusk, bloom, pollen, haze


def _spec_fable_nightbloom(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_18, seed)
    dusk, bloom, pollen, haze = _nightbloom_fields(h, w, s)
    sparkle = _msc(h, w, [2, 4], s ^ 0x18E5)
    rgrain = _msc(h, w, [3, 7, 16], s ^ 0x18F6)
    # M = pollen micro-stars (own scatter), Cc = the petal-fan artwork itself,
    # R = its own dusk haze + grain. The bloom show belongs to the clearcoat.
    M = 22.0 + pollen * 226.0 + sparkle * 16.0
    R = 158.0 - haze * 92.0 + (rgrain - 0.5) * 52.0
    Cc = 28.0 + bloom * 202.0 + dusk * 20.0
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_nightbloom(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_18, seed)
    dusk, bloom, _pollen, _haze = _nightbloom_fields(h, w, s)
    base = _opt_oklch_ramp([(0.066, 0.058, 0.168), (0.135, 0.072, 0.225),
                       (0.238, 0.098, 0.208)], dusk, flatten_lightness=0.45)
    hint = bloom[:, :, None] * np.array([0.55, 0.30, 0.62], np.float32) * 0.11
    flake = (_msc(h, w, [2, 5], s ^ 0x1807) - 0.5) * 0.030
    eff = base + hint + flake[:, :, None] * np.array([0.8, 0.7, 1.0], np.float32)
    eff = np.clip(eff, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE 19) MAGNETITE FLOW — ferrofluid spike clusters, each with its own
# field orientation: hex-packed spike lattices (three interfering plane waves
# 120 degrees apart, rotated per cluster, organically warped) inside hard
# supergaussian envelopes, floating on WET BLACK. Paint = Beer–Lambert candy:
# a steel-blue metal layer under a dark coat that pools deep between spikes
# and thins to bright steel at the crests. Spec choreography: M flares ONLY
# the spike tips, R is whole-canvas flow-aligned anisotropic grain (angle
# owned by the nearest cluster), Cc pools on its own smooth field.
# ============================================================================
FAB_19 = "fable_magnetite_flow"


def _magnetite_flow_fields(h, w, seed):
    """Per scattered cluster: a rotated hex spike lattice (own orientation)
    gives sharp TIPS + cone RELIEF inside a hard supergaussian envelope. The
    whole canvas also gets anisotropic flow grain whose direction is owned by
    the NEAREST cluster — multi-angle by construction, no global direction."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    px = m / 1024.0
    wamt = 3.2 * px
    wx = (_msc(h, w, [9, 23], seed ^ 0x19A5) - 0.5) * 2.0 * wamt
    wy = (_msc(h, w, [9, 23], seed ^ 0x19B6) - 0.5) * 2.0 * wamt
    warp = (_msc(h, w, [18, 44], seed ^ 0x19E5) - 0.5) * 2.0
    tips = np.zeros((h, w), np.float32)
    relief = np.zeros((h, w), np.float32)
    env = np.zeros((h, w), np.float32)
    cys = np.empty(14, np.float32)
    cxs = np.empty(14, np.float32)
    cosa = np.empty(14, np.float32)
    sina = np.empty(14, np.float32)
    for _i in range(14):
        cy = float(rng.uniform(0.0, h))
        cx = float(rng.uniform(0.0, w))
        ang = float(rng.uniform(0.0, 2.0 * np.pi))
        reach = float(rng.uniform(0.07, 0.13)) * m
        p = max(float(rng.uniform(13.0, 21.0)) * px, 4.0)
        k = 2.0 * np.pi / p
        cys[_i] = cy
        cxs[_i] = cx
        cosa[_i] = float(np.cos(ang))
        sina[_i] = float(np.sin(ang))
        # envelope support: exp(-((3.1^2/2))^1.4) ~ 1e-4 -> window the cluster
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, 3.1 * reach)
        dy = yy[y0:y1, x0:x1] - cy
        dx = xx[y0:y1, x0:x1] - cx
        r2 = dx * dx + dy * dy
        e = np.exp(-(r2 / (2.0 * reach * reach)) ** 1.4)
        dxw = dx + wx[y0:y1, x0:x1]
        dyw = dy + wy[y0:y1, x0:x1]
        f = np.zeros_like(dx)
        for j in range(3):
            aj = ang + j * (2.0 * np.pi / 3.0)
            ph = float(rng.uniform(0.0, 2.0 * np.pi))
            f += np.cos((dxw * float(np.cos(aj)) + dyw * float(np.sin(aj))) * k + ph)
        f *= (1.0 / 3.0)
        np.maximum(tips[y0:y1, x0:x1], (np.clip(f, 0.0, 1.0) ** 7) * e,
                   out=tips[y0:y1, x0:x1])
        np.maximum(relief[y0:y1, x0:x1], ((f + 1.0) * 0.5) ** 1.6 * e,
                   out=relief[y0:y1, x0:x1])
        np.maximum(env[y0:y1, x0:x1], e, out=env[y0:y1, x0:x1])
    # streak: nearest-cluster ownership (bit-identical f32 metric via cKDTree
    # candidates), then the owner's flow-aligned scanline — same math
    _, _, own = _opt_voro_top2(yy, xx, cys, cxs, k=4)
    v = ((yy - cys[own]) + wy) * cosa[own] - ((xx - cxs[own]) + wx) * sina[own]
    streak = (0.5 + 0.5 * np.sin(v * (2.0 * np.pi) / max(4.6 * px, 2.2)
                                 + warp * 5.2)).astype(np.float32)
    pool = _msc(h, w, [55, 130, 290], seed ^ 0x19F6)
    return (tips.astype(np.float32), relief.astype(np.float32),
            env.astype(np.float32), streak, pool)


def _spec_fable_magnetite_flow(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_19, seed)
    tips, relief, env, streak, pool = _magnetite_flow_fields(h, w, s)
    micro = _msc(h, w, [2, 4], s ^ 0x1901)
    # M = spike TIPS only (sparse hard flares); R = flow-aligned aniso grain
    # (own whole-canvas geometry); Cc = pooling on its OWN smooth field with
    # only small envelope/relief cross-terms.
    M = 18.0 + tips * 232.0 + micro * 16.0
    R = 168.0 - streak * 118.0 - tips * 22.0
    Cc = 28.0 + pool * 160.0 + env * 28.0 - relief * 20.0
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_magnetite_flow(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_19, seed)
    tips, relief, env, streak, pool = _magnetite_flow_fields(h, w, s)
    flow = np.clip(0.16 + relief * 0.70 + (streak - 0.5) * 0.12, 0.0, 1.0)
    metal = _opt_oklch_ramp([(0.235, 0.285, 0.365), (0.45, 0.54, 0.66),
                        (0.86, 0.91, 0.97)], flow)
    depth = 1.60 - 1.38 * relief
    eff = candy_absorb(metal, np.array([0.30, 0.38, 0.55], np.float32), depth)
    eff = eff + tips[:, :, None] * np.array([0.70, 0.80, 0.95], np.float32) * 0.32
    eff = eff + (pool[:, :, None] - 0.5) * np.array([0.016, 0.024, 0.040], np.float32)
    eff = np.clip(eff, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE 20) COMET PARADE — three INDEPENDENT comet populations, one per spec
# channel, no shared centers anywhere: M = bright heads + short tails that
# spark under direct sun; R = long soft wake streaks (signed light/dark gloss
# lanes) from a second population; Cc = bow-shock arc crescents from a third.
# Paint = deep-space violet→teal OKLab ramp with all three populations tinted
# in subtly, so every sun angle parades a different swarm.
# ============================================================================
FAB_20 = "fable_comet_parade"


def _comet_parade_heads(h, w, seed):
    """Population 1 (M): bright comet heads + short decaying tails; every
    comet has its own center and heading angle."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    px = m / 1024.0
    acc = np.zeros((h, w), np.float32)
    for _ in range(64):
        cy = float(rng.uniform(0.0, h))
        cx = float(rng.uniform(0.0, w))
        ang = float(rng.uniform(0.0, 2.0 * np.pi))
        tl = float(rng.uniform(14.0, 42.0)) * px
        sv = max(float(rng.uniform(1.6, 3.0)) * px, 0.9)
        amp = float(rng.uniform(0.55, 1.0))
        ca = float(np.cos(ang))
        sa = float(np.sin(ang))
        y0, y1, x0, x1 = _opt_rect_win(h, w, cy, cx, ca, sa,
                                       -9.0 * px, 7.0 * tl,
                                       max(4.5 * sv, 9.0 * px))
        dy = yy[y0:y1, x0:x1] - cy
        dx = xx[y0:y1, x0:x1] - cx
        u = dx * ca + dy * sa
        v = dy * ca - dx * sa
        head = np.exp(-(u * u + v * v) / (2.0 * max(2.2 * px, 1.1) ** 2))
        tail = (np.exp(-np.maximum(u, 0.0) / tl)
                * np.exp(-(v * v) / (2.0 * sv * sv))
                * (u > -2.0 * px))
        sub = acc[y0:y1, x0:x1]
        np.maximum(sub, np.maximum(head, tail * 0.8) * amp, out=sub)
    return np.clip(acc, 0.0, 1.0).astype(np.float32)


def _comet_parade_wakes(h, w, seed):
    """Population 2 (R): long SOFT wake streaks, signed light/dark, returned
    re-centered into [0,1] with 0.5 = neutral. Different centers than pop 1."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    px = m / 1024.0
    acc = np.zeros((h, w), np.float32)
    for _ in range(34):
        cy = float(rng.uniform(0.0, h))
        cx = float(rng.uniform(0.0, w))
        ang = float(rng.uniform(0.0, 2.0 * np.pi))
        wl = float(rng.uniform(90.0, 240.0)) * px
        sv = float(rng.uniform(4.0, 9.0)) * px
        sgn = 1.0 if rng.random() < 0.5 else -1.0
        amp = float(rng.uniform(0.45, 0.9)) * sgn
        ca = float(np.cos(ang))
        sa = float(np.sin(ang))
        y0, y1, x0, x1 = _opt_rect_win(h, w, cy, cx, ca, sa,
                                       -3.0 * px, 6.0 * wl, 4.5 * sv)
        dy = yy[y0:y1, x0:x1] - cy
        dx = xx[y0:y1, x0:x1] - cx
        u = dx * ca + dy * sa
        v = dy * ca - dx * sa
        wake = (np.exp(-np.maximum(u, 0.0) / wl)
                * np.exp(-(v * v) / (2.0 * sv * sv))
                * (u > -3.0 * px))
        acc[y0:y1, x0:x1] += wake * amp
    return np.clip(0.5 + 0.5 * acc, 0.0, 1.0).astype(np.float32)


def _comet_parade_shocks(h, w, seed):
    """Population 3 (Cc): bow-shock arc crescents — a sharp arc plus a fainter
    outer shock layer, each on its own center/heading."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    px = m / 1024.0
    acc = np.zeros((h, w), np.float32)
    for _ in range(44):
        cy = float(rng.uniform(0.0, h))
        cx = float(rng.uniform(0.0, w))
        ang = float(rng.uniform(0.0, 2.0 * np.pi))
        r0 = float(rng.uniform(10.0, 34.0)) * px
        lw = max(float(rng.uniform(2.2, 4.5)) * px, 1.1)
        spread = float(rng.uniform(0.55, 1.0))
        amp = float(rng.uniform(0.55, 1.0))
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, r0 * 1.5 + 7.0 * lw)
        dy = yy[y0:y1, x0:x1] - cy
        dx = xx[y0:y1, x0:x1] - cx
        r = np.sqrt(dy * dy + dx * dx) + 1e-6
        th = np.arctan2(dy, dx)
        d = np.mod(th - ang + np.pi, 2.0 * np.pi) - np.pi
        window = np.exp(-(d / spread) ** 2)
        crest = np.exp(-((r - r0) / lw) ** 2)
        outer = np.exp(-((r - r0 * 1.5) / (lw * 1.6)) ** 2) * 0.55
        sub = acc[y0:y1, x0:x1]
        np.maximum(sub, np.maximum(crest, outer) * window * amp, out=sub)
    return np.clip(acc, 0.0, 1.0).astype(np.float32)


def _comet_parade_fields(h, w, seed):
    heads = _comet_parade_heads(h, w, seed ^ 0x20A1)
    wakes = _comet_parade_wakes(h, w, seed ^ 0x20B2)
    shocks = _comet_parade_shocks(h, w, seed ^ 0x20C3)
    nebula = _msc(h, w, [44, 105, 240], seed ^ 0x20D4)
    return heads, wakes, shocks, nebula


def _spec_fable_comet_parade(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_20, seed)
    heads, wakes, shocks, _nebula = _comet_parade_fields(h, w, s)
    micro = _msc(h, w, [2, 4], s ^ 0x20E5)
    rgrain = _msc(h, w, [3, 8], s ^ 0x20F6)
    glow = _msc(h, w, [60, 150], s ^ 0x2007)
    # Three populations, three channels, zero shared centers = decorrelated
    # by construction. Each channel still gets its own micro/macro support.
    M = 22.0 + heads * 224.0 + micro * 18.0
    R = 150.0 + (wakes - 0.5) * 150.0 + (rgrain - 0.5) * 30.0
    Cc = 30.0 + shocks * 190.0 + glow * 28.0
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_comet_parade(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_20, seed)
    heads, wakes, shocks, nebula = _comet_parade_fields(h, w, s)
    base = _opt_oklch_ramp([(0.165, 0.050, 0.310), (0.075, 0.100, 0.330),
                       (0.025, 0.260, 0.270)], nebula, flatten_lightness=0.5)
    eff = (base
           + heads[:, :, None] * np.array([0.88, 0.80, 0.58], np.float32) * 0.30
           + (wakes[:, :, None] - 0.5) * np.array([0.05, 0.17, 0.19], np.float32)
           + shocks[:, :, None] * np.array([0.25, 0.62, 0.72], np.float32) * 0.20)
    stars = (_msc(h, w, [2, 5], s ^ 0x2018) - 0.5) * 0.026
    eff = eff + stars[:, :, None]
    eff = np.clip(eff, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ---------------------------------------------------------------------------
# REGISTRY EXPORT - engine/registry.py does mono_reg.update(FABLE_MONOLITHICS)
# ---------------------------------------------------------------------------
FABLE_MONOLITHICS = {
    FAB_1:  (_spec_fable_ember_glass, _paint_fable_ember_glass),
    FAB_2:  (_spec_fable_glacier_core, _paint_fable_glacier_core),
    FAB_3:  (_spec_fable_abyss_lantern, _paint_fable_abyss_lantern),
    FAB_4:  (_spec_fable_stained_aurora, _paint_fable_stained_aurora),
    FAB_5:  (_spec_fable_prism_veil, _paint_fable_prism_veil),
    FAB_6:  (_spec_fable_oilforge, _paint_fable_oilforge),
    FAB_7:  (_spec_fable_tempered_dawn, _paint_fable_tempered_dawn),
    FAB_8:  (_spec_fable_pulse_alloy, _paint_fable_pulse_alloy),
    FAB_9:  (_spec_fable_velvet_eclipse, _paint_fable_velvet_eclipse),
    FAB_10:  (_spec_fable_wovenlight, _paint_fable_wovenlight),
    FAB_11:  (_spec_fable_sovereign_flip, _paint_fable_sovereign_flip),
    FAB_12:  (_spec_fable_static_bloom, _paint_fable_static_bloom),
    FAB_13:  (_spec_fable_aurora_travel, _paint_fable_aurora_travel),
    FAB_14:  (_spec_fable_saffron_circuit, _paint_fable_saffron_circuit),
    FAB_15:  (_spec_fable_quicksilver_garden, _paint_fable_quicksilver_garden),
    FAB_16:  (_spec_fable_emberline_drift, _paint_fable_emberline_drift),
    FAB_17:  (_spec_fable_duomorph, _paint_fable_duomorph),
    FAB_18:  (_spec_fable_nightbloom, _paint_fable_nightbloom),
    FAB_19:  (_spec_fable_magnetite_flow, _paint_fable_magnetite_flow),
    FAB_20:  (_spec_fable_comet_parade, _paint_fable_comet_parade),
}


# === FABLE CRUSH-REBUILD 2026-06-09 (round 2) START ===
# Owner round-1 verdicts: 17 rebuild + 1 replace, all 'Too blobby / macro'.
# Later defs REBIND the finish fns; the .update below re-points the registry.
# Keepers velvet_eclipse / wovenlight stay on their original optimized blocks.


# ============================================================================
# FABLE — GLACIER CORE (fable_glacier_core) — CRUSHED-FINE REBUILD
# Owner verdict: "3-4x finer + too similar to another." Rebuild: the big
# Chebyshev shards are GONE — glacier is now micro shattered-frost: 3400 tiny
# ice needles/splinters (4-13px work, sub-px to 1.3px wide) stamped at
# per-needle random angles, each with a signed facet tilt so every splinter
# catches its own light. Needles etch THIN bright arctic-cyan scratches into
# a deep sapphire Beer-Lambert coat; frost-dust micro sparkle fills between.
# Totally distinct generator from ember_glass (no Voronoi web anywhere).
# Spec: M = its OWN second splinter set + frost glitter, R = 5-axis frost-
# feather micro grain, Cc = a third soft frost-filament glow set + current.
# ============================================================================
FAB_2 = "fable_glacier_core"


def _glacier_core_needles2(h, w, seed, count, ln_lo, ln_hi, wd_lo, wd_hi):
    """Micro ice splinters: windowed anisotropic line stamps at per-needle
    random angles -> (needle field, signed facet tilt along each needle)."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    mx = float(max(h, w))
    acc = np.zeros((h, w), np.float32)
    tilt = np.zeros((h, w), np.float32)
    for _ in range(count):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        ln = rng.uniform(ln_lo, ln_hi) * mx
        wd = max(0.55, rng.uniform(wd_lo, wd_hi) * mx)
        ang = rng.uniform(0.0, np.pi)
        amp = rng.uniform(0.45, 1.0)
        sgn = 1.0 if rng.random() < 0.5 else -1.0
        ca = float(np.cos(ang))
        sa = float(np.sin(ang))
        y0, y1, x0, x1 = _opt_rect_win(h, w, cy, cx, ca, sa, -ln, ln, 3.0 * wd)
        dy = yy[y0:y1, x0:x1] - cy
        dx = xx[y0:y1, x0:x1] - cx
        u = dx * ca + dy * sa
        v = dy * ca - dx * sa
        un = np.clip(u / ln, -1.0, 1.0)
        prof = np.exp(-(v * v) / (2.0 * wd * wd)) * np.clip(1.0 - un * un, 0.0, 1.0)
        acc[y0:y1, x0:x1] += prof * amp
        tilt[y0:y1, x0:x1] += prof * amp * sgn * un
    return np.clip(acc, 0.0, 1.6).astype(np.float32), np.clip(tilt, -1.0, 1.0).astype(np.float32)


def _glacier_core_fields2(h, w, seed):
    """-> (needles, facet tilt, frost dust, candy depth, drift macro)."""
    mx = float(max(h, w))
    ndl, tilt = _glacier_core_needles2(h, w, seed ^ 0x61CE, 5200, 0.003, 0.008, 0.0006, 0.0011)
    rng = np.random.default_rng((seed ^ 0xD057) & 0x7FFFFFFF)
    du = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32), (0, 0), 0.55)
    dust = np.clip((du - 0.62) / 0.38, 0.0, 1.0) ** 1.6
    drift = _msc(h, w, [max(9, int(mx * 0.08)), max(17, int(mx * 0.22))], seed ^ 0x1CEB)
    nd = np.clip(ndl, 0.0, 1.0)
    depth = np.clip(1.05 + (drift - 0.5) * 0.16 - nd * 0.85 - dust * 0.45, 0.06, 2.4)
    return ndl, tilt, dust, depth.astype(np.float32), drift


def _spec_fable_glacier_core(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_2, seed)
    mx = float(max(h, w))

    # M — its OWN hidden splinter set flashes under raking light + glitter
    mndl, _mt = _glacier_core_needles2(h, w, s ^ 0x91F7, 2200, 0.0025, 0.007, 0.0006, 0.0011)
    rngm = np.random.default_rng((s ^ 0x91F8) & 0x7FFFFFFF)
    gl = cv2.GaussianBlur(rngm.random((h, w)).astype(np.float32), (0, 0), 0.55)
    glit = np.clip((gl - 0.78) / 0.22, 0.0, 1.0) ** 2.0
    patch = _msc(h, w, [max(13, int(mx * 0.16))], s ^ 0x91F9)
    M = 22.0 + np.clip(mndl, 0.0, 1.0) * 160.0 + glit * 150.0 + patch * 30.0

    # R — 5-axis frost-feather micro grain (own field)
    rngr = np.random.default_rng((s ^ 0xA3D9) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    feather = np.zeros((h, w), np.float32)
    for k in range(5):
        ang = rngr.uniform(0.0, np.pi)
        per = rngr.uniform(0.0026, 0.0050) * mx
        ph = _msc(h, w, [max(5, int(mx * 0.04))], (s ^ 0xA3E0) + 3 * k)
        feather += np.sin((xx * np.cos(ang) + yy * np.sin(ang)) * (2.0 * np.pi / per) + ph * 7.0)
    feather = feather / 5.0 * 0.5 + 0.5
    ice_g = _msc(h, w, [2, max(5, int(mx * 0.006)), max(11, int(mx * 0.02))], s ^ 0xA3F1)
    R = 68.0 + feather * 74.0 + (ice_g - 0.5) * 70.0

    # Cc — third soft frost-filament glow set + deep current
    cndl, _ct = _glacier_core_needles2(h, w, s ^ 0xC01D, 1100, 0.004, 0.009, 0.0015, 0.0026)
    glow = cv2.GaussianBlur(np.clip(cndl, 0.0, 1.2), (0, 0), 1.5)
    current = _msc(h, w, [max(9, int(mx * 0.09)), max(17, int(mx * 0.26))], s ^ 0xC01E)
    Cc = 40.0 + glow * 150.0 + (current - 0.5) * 55.0

    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_glacier_core(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_2, seed)
    mx = float(max(h, w))
    ndl, tilt, dust, depth, drift = _glacier_core_fields2(h, w, s)
    sheen = _msc(h, w, [max(3, int(mx * 0.018)), max(7, int(mx * 0.06))], s ^ 0xB10C)
    fgr = _msc(h, w, [2, max(4, int(mx * 0.005))], s ^ 0xB10D)
    metal_g = np.clip(0.52 + tilt * 0.30 + dust * 0.30 + (sheen - 0.5) * 0.08
                      + (fgr - 0.5) * 0.16, 0.0, 1.0)
    metal = metal_g[:, :, None] * np.array([0.94, 0.985, 1.0], np.float32)
    stops = [(0.30, 0.95, 0.98), (0.05, 0.55, 0.90), (0.04, 0.16, 0.60)]
    nd = np.clip(ndl, 0.0, 1.0)
    t = np.clip(0.78 - nd * 0.52 - dust * 0.22 + (drift - 0.5) * 0.16, 0.0, 1.0)
    tint = _opt_oklch_ramp(stops, t, flatten_lightness=0.45, exact_edges=True)
    eff = candy_absorb(metal, tint, depth, density=1.0)
    rim = _edge(nd, gain=4.0)
    eff = eff + rim[:, :, None] * np.array([0.10, 0.20, 0.26], np.float32) * 0.45
    eff = _upscale(np.clip(eff, 0.0, 1.0).astype(np.float32), fh, fw)
    # native-res frost glitter: true flake-scale sparkle at canvas res
    rngfr = np.random.default_rng((s ^ 0xF057) & 0x7FFFFFFF)
    fr = rngfr.random((fh, fw)).astype(np.float32)
    spark = cv2.GaussianBlur(np.clip((fr - 0.78) / 0.22, 0.0, 1.0) ** 1.5, (0, 0), 0.45)
    mg = 0.85 + 0.55 * spark
    eff = np.clip(eff * mg[:, :, None], 0.004, 0.99)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE — GEMCRUSH AURORA (fable_stained_aurora) — REPLACEMENT CONCEPT
# Owner verdict on Stained Aurora: REPLACE. New idea in this slot (id kept):
# crushed cathedral glass at MICRO-MOSAIC scale — 8500 angular jewel chips
# (rotated-Chebyshev Voronoi, ~11px work) each cut to its own random facet
# axis and its own jewel hue (ruby/amber/emerald/sapphire/violet OKLCH ramp),
# leaded with ~1px hairline grout where the candy POOLS dark, dusted with
# dichroic teal/magenta micro-glitter, the whole field drifting under a slow
# aurora. A third of the chips are mirror-polished: under raking light the
# mosaic flips color (perceptual flip lattice at CHIP scale in M).
# Spec: M = mirror-chip flip lattice + star glints, R = own hammered micro
# grain, Cc = own scattered micro-glow points + aurora pooling.
# UV-agnostic: per-chip random rotation AND facet axis; isotropic scatter.
# ============================================================================
FAB_4 = "fable_stained_aurora"


def _stained_aurora_chips(h, w, seed, count):
    """Rotated-Chebyshev micro-Voronoi: thousands of angular crushed-glass
    chips -> (facet shade, grout web, chip hue rand, chip depth rand, mirror)."""
    mx = float(max(h, w))
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    py = rng.uniform(0, h, count).astype(np.float32)
    px = rng.uniform(0, w, count).astype(np.float32)
    th = rng.uniform(0.0, 0.5 * np.pi, count).astype(np.float32)
    ga = rng.uniform(0.0, 2.0 * np.pi, count).astype(np.float32)
    tc = rng.random(count).astype(np.float32)
    dc = rng.uniform(0.55, 1.9, count).astype(np.float32)
    mir = (rng.random(count) < 0.34).astype(np.float32)
    cs = np.cos(th).astype(np.float32)
    sn = np.sin(th).astype(np.float32)
    cga = np.cos(ga).astype(np.float32)
    sga = np.sin(ga).astype(np.float32)
    from scipy.spatial import cKDTree
    tree = cKDTree(np.stack([py.astype(np.float64), px.astype(np.float64)], axis=1))
    K = min(6, count)
    d1 = np.empty((h, w), np.float32)
    d2 = np.empty((h, w), np.float32)
    idx = np.empty((h, w), np.int32)
    big = np.int32(1 << 30)
    step = max(16, int((4 << 20) // max(w * K, 1)))
    for y0 in range(0, h, step):
        y1 = min(y0 + step, h)
        yb = yy[y0:y1]
        xb = xx[y0:y1]
        _, cand = tree.query(np.stack([yb.ravel(), xb.ravel()], axis=1), k=K, workers=-1)
        cand = cand.astype(np.int32).reshape(y1 - y0, w, K)
        dy = yb[:, :, None] - py[cand]
        dx = xb[:, :, None] - px[cand]
        csg = cs[cand]
        sng = sn[cand]
        u = np.abs(dx * csg + dy * sng)
        v = np.abs(dy * csg - dx * sng)
        dd = np.maximum(u, v)
        two = np.partition(dd, 1, axis=2)[:, :, :2]
        d1[y0:y1] = two[:, :, 0]
        d2[y0:y1] = two[:, :, 1]
        idx[y0:y1] = np.where(dd <= two[:, :, :1], cand, big).min(axis=2)
    shade = ((xx - px[idx]) * cga[idx] + (yy - py[idx]) * sga[idx]) / (mx * 0.0070)
    shade = np.clip(shade * 0.5 + 0.5, 0.0, 1.0).astype(np.float32)
    grout = np.exp(-(d2 - d1) / (mx * 0.0009)).astype(np.float32)
    return shade, grout, tc[idx].astype(np.float32), dc[idx].astype(np.float32), mir[idx].astype(np.float32)


def _stained_aurora_glowpts(h, w, seed, count):
    """Scattered micro-glow points (Cc's own primary geometry)."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    mx = float(max(h, w))
    acc = np.zeros((h, w), np.float32)
    for _ in range(count):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        rad = max(0.9, rng.uniform(0.0018, 0.005) * mx)
        amp = rng.uniform(0.5, 1.0)
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, 3.0 * rad + 1.5)
        r2 = (yy[y0:y1, x0:x1] - cy) ** 2 + (xx[y0:y1, x0:x1] - cx) ** 2
        acc[y0:y1, x0:x1] += np.exp(-r2 / (2.0 * rad * rad)) * amp
    return np.clip(acc, 0.0, 1.3).astype(np.float32)


def _stained_aurora_fields2(h, w, seed):
    """-> (facet shade, grout web, per-chip hue t, candy depth, mirror mask)."""
    mx = float(max(h, w))
    shade, grout, tc, dcm, mir = _stained_aurora_chips(h, w, seed ^ 0x57A1, 12000)
    aur = _msc(h, w, [max(9, int(mx * 0.09)), max(17, int(mx * 0.24))], seed ^ 0x57F3)
    t = np.clip(tc * 0.85 + (aur - 0.5) * 0.18 + 0.11, 0.0, 1.0).astype(np.float32)
    depth = np.clip(dcm * (0.72 + grout * 0.85), 0.12, 2.8).astype(np.float32)
    return shade, grout, t, depth, mir


def _spec_fable_stained_aurora(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_4, seed)
    mx = float(max(h, w))
    shade, grout, _t, _depth, mir = _stained_aurora_fields2(h, w, s)

    # M — mirror-chip flip lattice (1/3 of chips flare under raking light)
    rngm = np.random.default_rng((s ^ 0x3A10) & 0x7FFFFFFF)
    g = cv2.GaussianBlur(rngm.random((h, w)).astype(np.float32), (0, 0), 0.55)
    star = np.clip((g - 0.80) / 0.20, 0.0, 1.0) ** 2.0
    M = (20.0 + mir * (150.0 + 60.0 * shade) + star * 130.0) \
        * (1.0 - np.clip(grout * 1.2, 0.0, 1.0) * 0.75)

    # R — own hammered micro grain + slow swell
    ham = _msc(h, w, [2, max(5, int(mx * 0.005)), max(11, int(mx * 0.016))], s ^ 0x3B21)
    swl = _msc(h, w, [max(13, int(mx * 0.12))], s ^ 0x3B22)
    R = 66.0 + ham * 96.0 + (swl - 0.5) * 60.0

    # Cc — own scattered micro-glow points + aurora pooling
    glowp = _stained_aurora_glowpts(h, w, s ^ 0x3C32, 850)
    pool = _msc(h, w, [max(9, int(mx * 0.1)), max(17, int(mx * 0.3))], s ^ 0x3C33)
    Cc = 40.0 + glowp * 150.0 + (pool - 0.5) * 70.0

    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_stained_aurora(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_4, seed)
    shade, grout, t, depth, _mir = _stained_aurora_fields2(h, w, s)
    rngp = np.random.default_rng((s ^ 0x6E40) & 0x7FFFFFFF)
    sp = cv2.GaussianBlur(rngp.random((h, w)).astype(np.float32), (0, 0), 0.55)
    spark = np.clip((sp - 0.70) / 0.30, 0.0, 1.0) ** 1.7
    metal_g = np.clip(0.53 + (shade - 0.5) * 0.36 + spark * 0.32, 0.0, 1.0)
    metal = metal_g[:, :, None] * np.array([0.99, 0.985, 0.97], np.float32)
    stops = [(0.66, 0.04, 0.12), (0.97, 0.58, 0.08), (0.06, 0.58, 0.27),
             (0.05, 0.24, 0.78), (0.46, 0.10, 0.66)]
    tint = _opt_oklch_ramp(stops, t, flatten_lightness=0.55)
    eff = candy_absorb(metal, tint, depth, density=1.0)
    gm = np.clip(grout * 1.25, 0.0, 1.0)[:, :, None]
    eff = eff * (1.0 - gm) + np.array([0.05, 0.05, 0.065], np.float32) * gm
    eff = _upscale(np.clip(eff, 0.0, 1.0).astype(np.float32), fh, fw)
    # dichroic micro-glitter at TRUE canvas flake scale: 1-2px specks that
    # flip teal/magenta on a blurred-noise lattice (native res, post-upscale)
    rngl = np.random.default_rng((s ^ 0x6E51) & 0x7FFFFFFF)
    lat = (cv2.GaussianBlur(rngl.random((fh, fw)).astype(np.float32), (0, 0), 0.6)
           > 0.5).astype(np.float32)
    g2 = np.random.default_rng((s ^ 0x6E62) & 0x7FFFFFFF).random((fh, fw)).astype(np.float32)
    fleck = np.clip(cv2.GaussianBlur((g2 > 0.975).astype(np.float32), (0, 0), 0.5) * 2.4, 0.0, 1.0)
    dichro = (lat[:, :, None] * np.array([0.25, 0.78, 0.86], np.float32)
              + (1.0 - lat)[:, :, None] * np.array([0.88, 0.22, 0.78], np.float32))
    eff = np.clip(eff + fleck[:, :, None] * dichro * 0.60, 0.004, 0.99)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE — EMBER GLASS (fable_ember_glass) — CRUSHED-FINE REBUILD
# Owner verdict: "Needs about 3-4x finer detail. Too big because of canvas
# size!" + flagged too-similar to glacier_core. Rebuild: the crackle went
# ~5.4x finer linear (110 -> 3200 warped micro-Voronoi sites; hairline gap web
# ~1.2px at work grid) and ember gains a NEW identity element glacier doesn't
# have: a blizzard of 2400 floating micro-cinders (1-4px white-hot sparks
# cooling to orange halos). The soul stays: blood-orange Beer-Lambert candy
# POOLING crimson-black inside the fissures.
# Spec: M = own micro flake-glint scatter + cinder flashes, R = own 4-axis
# micro brushed grain, Cc = the fissure glow web + own pooling macro.
# UV-agnostic: scattered sites, isotropic cinders, random brush axes.
# ============================================================================
FAB_1 = "fable_ember_glass"


def _ember_glass_microvoro(h, w, seed, count):
    """Noise-warped Euclidean micro-Voronoi -> (hairline crack web, cell rand)."""
    mx = float(max(h, w))
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    wy = (_msc(h, w, [max(3, int(mx * 0.012)), max(7, int(mx * 0.05))], seed ^ 0x1EA1) - 0.5) * mx * 0.012
    wx = (_msc(h, w, [max(3, int(mx * 0.012)), max(7, int(mx * 0.05))], seed ^ 0x1EA2) - 0.5) * mx * 0.012
    py = rng.uniform(0, h, count).astype(np.float32)
    px = rng.uniform(0, w, count).astype(np.float32)
    cr = rng.random(count).astype(np.float32)
    d1, d2, idx = _opt_voro_top2(yy + wy, xx + wx, py, px, k=4)
    gap = np.sqrt(d2) - np.sqrt(d1)
    crack = np.exp(-gap / (mx * 0.0012)).astype(np.float32)
    return crack, cr[idx].astype(np.float32)


def _ember_glass_cinders(h, w, seed, count):
    """Floating micro-cinders: windowed 1-4px ember sparks."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    mx = float(max(h, w))
    acc = np.zeros((h, w), np.float32)
    for _ in range(count):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        rad = max(0.55, rng.uniform(0.0008, 0.0022) * mx)
        amp = rng.uniform(0.5, 1.0)
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, 3.0 * rad + 1.5)
        r2 = (yy[y0:y1, x0:x1] - cy) ** 2 + (xx[y0:y1, x0:x1] - cx) ** 2
        acc[y0:y1, x0:x1] += np.exp(-r2 / (2.0 * rad * rad)) * amp
    return np.clip(acc, 0.0, 1.4).astype(np.float32)


@_memo_fields
def _ember_glass_fields2(h, w, seed):
    """-> (crack web, cell rand, cinders, flake, candy depth, macro drift)."""
    mx = float(max(h, w))
    crack, cr = _ember_glass_microvoro(h, w, seed ^ 0x0E1B, 9000)
    cind = _ember_glass_cinders(h, w, seed ^ 0xC1D2, 3200)
    rng_f = np.random.default_rng((seed ^ 0xF1AE) & 0x7FFFFFFF)
    fl = cv2.GaussianBlur(rng_f.random((h, w)).astype(np.float32), (0, 0), 0.55)
    flake = np.clip((fl - 0.60) / 0.40, 0.0, 1.0) ** 1.6
    macro = _msc(h, w, [max(9, int(mx * 0.07)), max(15, int(mx * 0.2))], seed ^ 0x77AA)
    depth = np.clip(0.42 + crack * 1.7 + (cr - 0.5) * 0.16 + (macro - 0.5) * 0.12
                    - np.clip(cind, 0.0, 1.0) * 0.50, 0.05, 3.0)
    return crack, cr, cind, flake, depth.astype(np.float32), macro


def _spec_fable_ember_glass(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_1, seed)
    mx = float(max(h, w))
    crack, _cr, cind, _flake, _depth, _macro = _ember_glass_fields2(h, w, s)

    # M — own micro flake-glint scatter + cinder flashes
    rngm = np.random.default_rng((s ^ 0x4D11) & 0x7FFFFFFF)
    g = cv2.GaussianBlur(rngm.random((h, w)).astype(np.float32), (0, 0), 0.55)
    glint = np.clip((g - 0.76) / 0.24, 0.0, 1.0) ** 2.0
    patch = _msc(h, w, [max(13, int(mx * 0.14))], s ^ 0x4D22)
    M = 26.0 + glint * 185.0 + np.clip(cind, 0.0, 1.0) * 110.0 + patch * 34.0

    # R — own 4-axis micro brushed grain
    rngr = np.random.default_rng((s ^ 0x52AA) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    brush = np.zeros((h, w), np.float32)
    for k in range(4):
        ang = rngr.uniform(0.0, np.pi)
        per = rngr.uniform(0.0026, 0.0048) * mx
        ph = _msc(h, w, [max(5, int(mx * 0.05))], (s ^ 0x52BB) + 3 * k)
        brush += np.sin((xx * np.cos(ang) + yy * np.sin(ang)) * (2.0 * np.pi / per) + ph * 6.0)
    brush = brush / 4.0 * 0.5 + 0.5
    grain_r = _msc(h, w, [2, max(5, int(mx * 0.006)), max(11, int(mx * 0.02))], s ^ 0x52CC)
    R = 72.0 + brush * 76.0 + (grain_r - 0.5) * 70.0

    # Cc — fissure glow web (raking-light ember veins) + own pooling
    web = cv2.GaussianBlur(crack, (0, 0), 1.2)
    pool = _msc(h, w, [max(9, int(mx * 0.1)), max(17, int(mx * 0.26))], s ^ 0x6CC3)
    Cc = 42.0 + web * 175.0 + (pool - 0.5) * 55.0

    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_ember_glass(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_1, seed)
    mx = float(max(h, w))
    crack, cr, cind, flake, depth, macro = _ember_glass_fields2(h, w, s)
    sheen = _msc(h, w, [max(3, int(mx * 0.02)), max(7, int(mx * 0.06))], s ^ 0x9B01)
    metal_g = np.clip(0.58 + (sheen - 0.5) * 0.10 + flake * 0.40, 0.0, 1.0)
    metal = metal_g[:, :, None] * np.array([0.985, 0.975, 0.96], np.float32)
    stops = [(0.93, 0.42, 0.06), (0.80, 0.16, 0.04), (0.52, 0.03, 0.07)]
    t = np.clip(0.24 + macro * 0.18 + cr * 0.24 + crack * 0.22, 0.0, 1.0)
    tint = _opt_oklch_ramp(stops, t, flatten_lightness=0.30, exact_edges=True)
    eff = candy_absorb(metal, tint, depth, density=1.0)
    core = np.clip(cind * 1.6 - 0.5, 0.0, 1.0)
    eff = (eff + cind[:, :, None] * np.array([0.55, 0.18, 0.02], np.float32) * 0.55
           + core[:, :, None] * np.array([0.42, 0.32, 0.10], np.float32) * 0.50)
    eff = _upscale(np.clip(eff, 0.0, 1.0).astype(np.float32), fh, fw)
    # native-res metal-flake glitter: true flake-scale energy at canvas res
    rngfr = np.random.default_rng((s ^ 0xFA9E) & 0x7FFFFFFF)
    fr = rngfr.random((fh, fw)).astype(np.float32)
    spark = cv2.GaussianBlur(np.clip((fr - 0.76) / 0.24, 0.0, 1.0) ** 1.5, (0, 0), 0.45)
    mg = 0.83 + 0.62 * spark
    eff = np.clip(eff * mg[:, :, None], 0.004, 0.99)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE — ABYSS LANTERN (fable_abyss_lantern) — CRUSHED-FINE REBUILD
# Owner verdict: "Need about 30x more circles and for them to be much
# smaller." Rebuild: 24 big lanterns -> 1150 micro lantern points (1.6-5px
# work radius, ~48x more) each with a tight membrane micro-ring, plus NEW
# plankton-fine bioluminescent glow webs (level-set filaments of a fine noise
# field, 1-2px) that thread between the lanterns. Near-black deep-sea teal
# Beer-Lambert absorption stays the soul; the lanterns thin the coat so each
# point glows teal-green through the murk.
# Spec: M = own plankton micro-glints, R = own abyssal-silt micro grain,
# Cc = THE lantern field + rings + glow web (raking-light reveal).
# UV-agnostic: isotropic point scatter, isotropic filaments, 3 random current
# axes; no global gradient.
# ============================================================================
FAB_3 = "fable_abyss_lantern"


def _abyss_lantern_micro(h, w, seed, count):
    """Hundreds of micro lantern points -> (glow cores, membrane micro rings)."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    mx = float(max(h, w))
    glow = np.zeros((h, w), np.float32)
    ring = np.zeros((h, w), np.float32)
    for _ in range(count):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        rad = max(0.8, rng.uniform(0.0009, 0.0024) * mx)
        amp = rng.uniform(0.5, 1.0)
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, 3.3 * rad + 1.5)
        r2 = (yy[y0:y1, x0:x1] - cy) ** 2 + (xx[y0:y1, x0:x1] - cx) ** 2
        glow[y0:y1, x0:x1] += np.exp(-r2 / (2.0 * rad * rad)) * amp
        rr = np.sqrt(r2)
        ring[y0:y1, x0:x1] += np.exp(-(((rr - rad * 1.8) / (rad * 0.40)) ** 2)) * amp * 0.8
    return np.clip(glow, 0.0, 1.5).astype(np.float32), np.clip(ring, 0.0, 1.2).astype(np.float32)


def _abyss_lantern_fields2(h, w, seed):
    """-> (lantern glow, micro rings, plankton web, murk, currents)."""
    mx = float(max(h, w))
    glow, ring = _abyss_lantern_micro(h, w, seed ^ 0xAB15, 4200)
    n = _msc(h, w, [max(3, int(mx * 0.004)), max(5, int(mx * 0.010))], seed ^ 0x9EB7)
    web = np.exp(-np.abs(n - 0.5) / 0.013).astype(np.float32)
    murk = _msc(h, w, [max(13, int(mx * 0.12)), max(23, int(mx * 0.3))], seed ^ 0x0DEE)
    rng = np.random.default_rng((seed ^ 0xC4BD) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    cur = np.zeros((h, w), np.float32)
    for k in range(3):
        ang = rng.uniform(0.0, np.pi)
        proj = (xx * np.cos(ang) + yy * np.sin(ang)) / mx
        ph = _msc(h, w, [max(9, int(mx * 0.1))], (seed ^ 0xC4C0) + 7 * k)
        cur += np.sin(proj * (40.0 + 16.0 * rng.random()) + ph * 7.0)
    cur = (cur / 3.0 * 0.5 + 0.5).astype(np.float32)
    return glow, ring, web, murk, cur


def _spec_fable_abyss_lantern(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_3, seed)
    mx = float(max(h, w))
    glow, ring, web, _murk, _cur = _abyss_lantern_fields2(h, w, s)

    # M — its own plankton micro-glints + faint drift patches
    rngm = np.random.default_rng((s ^ 0x9A4F) & 0x7FFFFFFF)
    pk = rngm.random((h, w)).astype(np.float32)
    plank = np.clip(cv2.GaussianBlur(np.clip((pk - 0.988) / 0.012, 0.0, 1.0), (0, 0), 0.7) * 3.0,
                    0.0, 1.0)
    drift = _msc(h, w, [max(11, int(mx * 0.12)), max(19, int(mx * 0.3))], s ^ 0x9A50)
    M = 16.0 + plank * 215.0 + drift * 32.0

    # R — abyssal silt micro grain + swell (own fields)
    silt = _msc(h, w, [2, max(5, int(mx * 0.005)), max(11, int(mx * 0.018))], s ^ 0x517E)
    swell = _msc(h, w, [max(17, int(mx * 0.26))], s ^ 0x517F)
    R = 64.0 + silt * 70.0 + (swell - 0.5) * 76.0

    # Cc — THE lantern choreography: cores + micro rings + plankton glow web
    Cc = 40.0 + np.clip(glow, 0.0, 1.2) * 135.0 + ring * 45.0 + web * 60.0

    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_abyss_lantern(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_3, seed)
    mx = float(max(h, w))
    glow, ring, web, murk, cur = _abyss_lantern_fields2(h, w, s)
    rngp = np.random.default_rng((s ^ 0x5EA1) & 0x7FFFFFFF)
    fl = cv2.GaussianBlur(rngp.random((h, w)).astype(np.float32), (0, 0), 0.6)
    flake = np.clip((fl - 0.70) / 0.30, 0.0, 1.0) ** 1.7
    silt_p = _msc(h, w, [2, max(4, int(mx * 0.005))], s ^ 0x5EA2)
    g1 = np.clip(glow, 0.0, 1.0)
    metal_g = np.clip(0.45 + flake * 0.34 + g1 * 0.22 + (silt_p - 0.5) * 0.20, 0.0, 1.0)
    metal = metal_g[:, :, None] * np.array([0.92, 1.0, 0.99], np.float32)
    stops = [(0.05, 0.66, 0.60), (0.03, 0.46, 0.50), (0.04, 0.30, 0.42)]
    t = np.clip(murk * 0.65 + cur * 0.35, 0.0, 1.0)
    tint = _opt_oklch_ramp(stops, t, flatten_lightness=0.40, exact_edges=True)
    depth = np.clip(1.20 + (murk - 0.5) * 0.08 + (cur - 0.5) * 0.06
                    - g1 * 0.75 - ring * 0.30 - web * 0.22, 0.50, 2.4)
    eff = candy_absorb(metal, tint, depth, density=1.0)
    eff = (eff + g1[:, :, None] * np.array([0.05, 0.22, 0.18], np.float32) * 0.7
           + ring[:, :, None] * np.array([0.02, 0.10, 0.09], np.float32) * 0.6
           + web[:, :, None] * np.array([0.02, 0.08, 0.08], np.float32) * 0.9)
    eff = _upscale(np.clip(eff, 0.0, 1.0).astype(np.float32), fh, fw)
    # native-res plankton dust: tiny teal sparks at true canvas flake scale
    rngfr = np.random.default_rng((s ^ 0xAB99) & 0x7FFFFFFF)
    fr = rngfr.random((fh, fw)).astype(np.float32)
    spark = cv2.GaussianBlur(np.clip((fr - 0.70) / 0.30, 0.0, 1.0) ** 1.5, (0, 0), 0.45)
    eff = np.clip(eff + spark[:, :, None] * np.array([0.10, 0.30, 0.26], np.float32) * 1.0,
                  0.004, 0.99)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE — PRISM VEIL (fable_prism_veil) — CRUSHED-FINE RETHINK
# Owner verdict: "Don't really love the finish... way too blobby." Rethink:
# the big drifting order patches are GONE. Prism Veil is now interference
# THREADWORK — a woven veil of hair-fine iridescent fibres (5 random-angle
# wavy thread families, 3-5px period, ~1px crests) over near-black cherry.
# Each thread carries quantized Newton-order color from a smooth multi-axis
# thickness field (orders=5, quantize=0.85), so the banded iridescence reads
# at THREAD scale and the hue migrates across the body. Scattered radial veil
# patches only breathe the thread density (low-contrast carrier).
# Spec: M = its OWN thread set + thin order-boundary flare lines, R = own
# satin micro field, Cc = own slow pooling + a third soft thread glow.
# UV-agnostic: 5 random axes + isotropic patches; no global gradient.
# ============================================================================
FAB_5 = "fable_prism_veil"


def _prism_veil_threadset(h, w, seed, n_axes):
    """Woven micro-thread lattice: n_axes random-angle wavy fibre families."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    mx = float(max(h, w))
    acc = np.zeros((h, w), np.float32)
    for k in range(n_axes):
        ang = rng.uniform(0.0, np.pi)
        per = rng.uniform(0.0030, 0.0054) * mx
        ph = rng.uniform(0.0, 2.0 * np.pi)
        wgt = rng.uniform(0.7, 1.0)
        warp = (_msc(h, w, [max(5, int(mx * 0.03)), max(9, int(mx * 0.08))],
                     (seed ^ 0x5E1F) + 7 * k) - 0.5) * 6.5
        tri = 0.5 + 0.5 * np.sin((xx * np.cos(ang) + yy * np.sin(ang))
                                 * (2.0 * np.pi / per) + ph + warp)
        acc += (tri ** 7).astype(np.float32) * wgt
    return np.clip(acc, 0.0, 1.3).astype(np.float32)


def _prism_veil_orders(h, w, seed):
    """Smooth multi-axis interference thickness field in [0,1]."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    mx = float(max(h, w))
    flow = np.zeros((h, w), np.float32)
    for _k in range(3):
        ang = rng.uniform(0.0, 2.0 * np.pi)
        wl = rng.uniform(0.05, 0.13) * mx
        flow += np.sin((xx * np.cos(ang) + yy * np.sin(ang)) * (2.0 * np.pi / wl)
                       + rng.uniform(0.0, 2.0 * np.pi)) * rng.uniform(0.6, 1.0)
    flow = (flow - flow.min()) / max(float(flow.max() - flow.min()), 1e-6)
    macro = _msc(h, w, [max(9, int(mx * 0.05)), max(15, int(mx * 0.12))], seed ^ 0x5EAA)
    return np.clip(flow * 0.62 + macro * 0.38, 0.0, 1.0).astype(np.float32)


def _prism_veil_splat2(acc, yy, xx, cy, cx, rad, ang, amp):
    """Soft isotropic veil patch (UV-orientation-free)."""
    r2 = (yy - cy) ** 2 + (xx - cx) ** 2
    sig = rad * 1.8
    acc += np.exp(-r2 / (2.0 * sig * sig)).astype(np.float32) * amp


def _spec_fable_prism_veil(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_5, seed)
    mx = float(max(h, w))
    thick = _prism_veil_orders(h, w, s ^ 0x5A15)

    # M — its OWN thread set flares + thin order-boundary lines
    thr2 = _prism_veil_threadset(h, w, s ^ 0x5A21, 3)
    q = np.floor(thick * 5.0).astype(np.float32)
    oedge = _edge(q * 0.25, gain=6.0)
    glint = _msc(h, w, [2, 4], s ^ 0x5A22)
    M = 22.0 + np.clip(thr2, 0.0, 1.0) * 150.0 + oedge * 120.0 + glint * 22.0

    # R — own satin micro field
    satin = _msc(h, w, [2, max(5, int(mx * 0.006)), max(11, int(mx * 0.016))], s ^ 0x5A23)
    R = 168.0 - satin * 120.0

    # Cc — own slow pooling + a third soft thread glow
    thr3 = _prism_veil_threadset(h, w, s ^ 0x5A24, 2)
    glow3 = cv2.GaussianBlur(np.clip(thr3, 0.0, 1.0), (0, 0), 1.4)
    pool = _msc(h, w, [max(13, int(mx * 0.1)), max(23, int(mx * 0.26))], s ^ 0x5A25)
    Cc = 32.0 + glow3 * 105.0 + pool * 90.0

    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_prism_veil(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_5, seed)
    threads = _prism_veil_threadset(h, w, s ^ 0x5A11, 5)
    thick = _prism_veil_orders(h, w, s ^ 0x5A15)
    veil = np.clip(_opt_scatter_field(h, w, s ^ 0x5A13, 90, _prism_veil_splat2,
                                      lambda rad: 3.2 * (rad * 1.8)), 0.0, 1.0)
    vw = 0.45 + 0.55 * veil
    flake = _msc(h, w, [2, 4], s ^ 0x5A14)
    film = interference_palette(thick, orders=5.0, quantize=0.85, brightness=0.90)
    cherry = np.empty((h, w, 3), np.float32)
    cherry[:, :, 0] = 0.055 + flake * 0.05
    cherry[:, :, 1] = 0.008 + flake * 0.014
    cherry[:, :, 2] = 0.018 + flake * 0.022
    tw = (np.clip(threads, 0.0, 1.0) * vw)[:, :, None]
    eff = cherry + film * tw * 0.92 + tw * 0.04
    eff = np.clip(eff, 0.004, 0.99).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE — OILFORGE (fable_oilforge) — CRUSHED-FINE REBUILD
# Owner verdict: "~25x more detail and much much smaller circles." Rebuild:
# 9-14 big heat zones -> 560 micro oil-ring epicenters (reach 4-9px work,
# ~17x smaller linear / ~49x more), each blooming tight quantized Newton
# rings (orders=7.5) with ~1-2px band spacing. Between systems: fine brushed
# gunmetal whose scratch direction snaps per Voronoi territory (3 random
# angles, ~2px micro streaks) + rare white micro sparks.
# Spec: M = ring crests, R = its OWN multi-angle micro brush grain (own
# territories + angles), Cc = heat glow half on its OWN epicenter set + pool.
# UV-agnostic: scattered epicenters, territory-snapped multi-angle grain.
# ============================================================================
FAB_6 = "fable_oilforge"


def _oilforge_micro_rings(h, w, seed, count):
    """Hundreds of micro oil-ring epicenters -> (thickness field, heat halo)."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    mx = float(max(h, w))
    thick = np.zeros((h, w), np.float32)
    halo = np.zeros((h, w), np.float32)
    for _ in range(count):
        cy = rng.uniform(0, h)
        cx = rng.uniform(0, w)
        reach = max(1.8, rng.uniform(0.0018, 0.0038) * mx)
        amp = rng.uniform(0.6, 1.0)
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, 3.0 * reach)
        r = np.sqrt((yy[y0:y1, x0:x1] - cy) ** 2 + (xx[y0:y1, x0:x1] - cx) ** 2)
        sub = thick[y0:y1, x0:x1]
        np.maximum(sub, np.exp(-r / reach).astype(np.float32) * amp, out=sub)
        halo[y0:y1, x0:x1] += np.exp(-((r / (reach * 1.5)) ** 2)).astype(np.float32) * amp * 0.5
    return thick, np.clip(halo, 0.0, 1.0).astype(np.float32)


def _oilforge_micrograin(h, w, seed):
    """Fine brushed-metal micro grain, scratch axis snapped per territory."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    mx = float(max(h, w))
    p0, p1, p2 = tri_partition((h, w), seed ^ 0x6FA1, cells=130, soften_px=max(1.5, mx / 500.0))
    out = np.zeros((h, w), np.float32)
    for i, msk in enumerate((p0, p1, p2)):
        ang = rng.uniform(0.0, np.pi)
        prof = rng.random(4096).astype(np.float32)
        v = (-np.sin(ang) * xx + np.cos(ang) * yy) * (1024.0 / mx)
        wob = (_msc(h, w, [max(7, int(mx * 0.05)), max(13, int(mx * 0.13))],
                    (seed ^ 0x6FB2) + 11 * i) - 0.5) * 5.0
        idx = np.mod((v + wob) * 1.9, 4096.0).astype(np.int32)
        out += msk * prof[idx]
    micro = _msc(h, w, [2, max(4, int(mx * 0.004))], seed ^ 0x6FC3)
    return (0.62 * out + 0.38 * micro).astype(np.float32)


def _spec_fable_oilforge(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_6, seed)
    mx = float(max(h, w))
    thick, halo = _oilforge_micro_rings(h, w, s ^ 0x6F10, 2800)
    pres = np.clip((thick - 0.12) * 9.0, 0.0, 1.0)
    bands = thick * 5.5
    frac = bands - np.floor(bands)
    crest = (np.exp(-((frac - 0.55) / 0.10) ** 2) * pres).astype(np.float32)
    glint = _msc(h, w, [2, 4], s ^ 0x6F31)
    M = 24.0 + crest * 195.0 + glint * 26.0

    # R — its OWN multi-angle micro brush grain (own territories + angles)
    grain_s = _oilforge_micrograin(h, w, s ^ 0x6F40)
    R = 176.0 - grain_s * 122.0

    # Cc — heat glow: half on its OWN epicenter set, half on the paint's
    _thick2, halo2 = _oilforge_micro_rings(h, w, s ^ 0x6F50, 1500)
    pool = _msc(h, w, [max(11, int(mx * 0.1)), max(21, int(mx * 0.26))], s ^ 0x6F32)
    Cc = 28.0 + halo * 62.0 + halo2 * 78.0 + pool * 42.0

    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_oilforge(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_6, seed)
    thick, halo = _oilforge_micro_rings(h, w, s ^ 0x6F10, 2800)
    grain = _oilforge_micrograin(h, w, s ^ 0x6F20)
    film = interference_palette(thick, orders=5.5, quantize=0.72, brightness=0.72)
    gm = (0.17 + grain * 0.24)[:, :, None] * np.array([0.94, 0.985, 1.07], np.float32)
    pres = (np.clip((thick - 0.12) * 9.0, 0.0, 1.0) * (0.62 + 0.15 * halo))[:, :, None]
    eff = gm * (1.0 - pres * 0.50) + film * pres * 0.66
    rngp = np.random.default_rng((s ^ 0x6F30) & 0x7FFFFFFF)
    sp = cv2.GaussianBlur(rngp.random((h, w)).astype(np.float32), (0, 0), 0.55)
    spark = np.clip((sp - 0.80) / 0.20, 0.0, 1.0) ** 2.0
    eff = eff + spark[:, :, None] * np.array([0.55, 0.58, 0.62], np.float32) * 0.26
    eff = _upscale(np.clip(eff, 0.0, 1.0).astype(np.float32), fh, fw)
    # native-res forge glitter: metal micro-sparkle at true canvas scale
    rngfr = np.random.default_rng((s ^ 0x6FF7) & 0x7FFFFFFF)
    fr = rngfr.random((fh, fw)).astype(np.float32)
    spk2 = cv2.GaussianBlur(np.clip((fr - 0.76) / 0.24, 0.0, 1.0) ** 1.5, (0, 0), 0.45)
    mgl = 0.84 + 0.60 * spk2
    eff = np.clip(eff * mgl[:, :, None], 0.004, 0.99)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE 7) TEMPERED DAWN — titanium micro-weld lacework (CRUSHED-FINE rebuild
# 2026-06-10, owner verdict "~50x more weld arcs, MUCH smaller"): ~520
# thread-thin random-walk weld arcs lace the whole panel; each arc carries
# quantized straw->bronze->violet->blue temper orders at THREAD scale (~2px
# work bands), with brushed raw-titanium micro crosshatch filling the gaps.
# Spec choreography: M = the 1px weld-bead lace itself (flares hard under
# direct sun) + lone micro pins; R = its OWN 3-axis micro crosshatch broken
# by wandering satin corridors (the highlight walks the lace); Cc = ember
# afterglow living on a SECOND, sparser arc set (own geometry, raking-angle
# ghost welds). UV-agnostic: every arc has its own random walk/heading.
# ============================================================================
FAB_7 = "fable_tempered_dawn"


def _tempered_dawn_arcs(h, w, seed, count, smin, smax):
    """Thread-thin random-walk weld arcs -> distance field in px (scatter
    placement loop only; cv2 draws + one distance transform do the work)."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    m = float(max(h, w))
    ink = np.zeros((h, w), np.uint8)
    for _ in range(count):
        steps = int(rng.integers(smin, smax))
        head = rng.uniform(0.0, 2.0 * np.pi) + np.cumsum(rng.normal(0.0, 0.30, steps))
        sl = rng.uniform(0.0018, 0.0032) * m
        py = rng.uniform(0.0, 1.0) * h + np.cumsum(np.sin(head) * sl)
        px = rng.uniform(0.0, 1.0) * w + np.cumsum(np.cos(head) * sl)
        pts = np.stack([np.clip(px, 1, w - 2), np.clip(py, 1, h - 2)], axis=1)
        cv2.polylines(ink, [pts.astype(np.int32).reshape(-1, 1, 2)], False, 255, 1)
    return cv2.distanceTransform((255 - ink).astype(np.uint8), cv2.DIST_L2, 3).astype(np.float32)


def _tempered_dawn_hatch(h, w, seed):
    """Raw-titanium micro crosshatch: 3 random-axis scratch sets at 2-3px."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    g = np.zeros((h, w), np.float32)
    warp = (_msc(h, w, [max(13, int(m * 0.045)), max(29, int(m * 0.11))], seed ^ 0x7D02) - 0.5) * 6.0
    for _k in range(3):
        ang = rng.uniform(0.0, np.pi)
        period = max(2.0, rng.uniform(2.0, 3.2) * (m / 1024.0))
        ph = rng.uniform(0.0, 2.0 * np.pi)
        proj = np.cos(ang) * xx + np.sin(ang) * yy
        srt = 0.5 + 0.5 * np.sin((proj + warp) * (2.0 * np.pi / period) + ph)
        np.maximum(g, (srt ** 3).astype(np.float32), out=g)
    return (0.72 * g + 0.28 * _msc(h, w, [2, 5], seed ^ 0x7D03)).astype(np.float32)


def _tempered_dawn_fields(h, w, seed):
    """-> (heat, bead): micro temper reach + 1px weld lace line."""
    sr = float(max(h, w)) / 1024.0
    dist = _tempered_dawn_arcs(h, w, seed ^ 0x7D10, 1400, 4, 8)
    heat = np.exp(-dist / (1.8 * sr)).astype(np.float32)
    bead = np.exp(-((dist / (0.75 * sr)) ** 2)).astype(np.float32)
    return heat, bead


def _spec_fable_tempered_dawn(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_7, seed)
    sr = float(max(h, w)) / 1024.0
    heat, bead = _tempered_dawn_fields(h, w, s)
    # M — the weld lace itself: 1px bead glints + rare lone pins in the field
    rngm = np.random.default_rng((s ^ 0x7D41) & 0x7FFFFFFF)
    pins = np.clip(cv2.GaussianBlur((rngm.random((h, w)) > 0.9975).astype(np.float32),
                                    (0, 0), 0.55) * 3.5, 0.0, 1.0)
    glint = _msc(h, w, [2, 4], s ^ 0x7D44)
    M = 22.0 + 206.0 * bead + 64.0 * pins * (1.0 - bead) + 20.0 * glint
    # R — its OWN micro crosshatch (own axes/seed) broken by satin corridors:
    # the live highlight walks the lace as the corridors sweep the car
    hatch_s = _tempered_dawn_hatch(h, w, s ^ 0x7D40)
    corr_n = _msc(h, w, [max(9, int(31 * sr)), max(19, int(73 * sr))], s ^ 0x7D45)
    lanes = np.clip((corr_n - 0.60) / 0.11, 0.0, 1.0)
    lanes = lanes * lanes * (3.0 - 2.0 * lanes)
    R = 166.0 - 110.0 * hatch_s - 42.0 * lanes + 18.0 * (_msc(h, w, [2, 5], s ^ 0x7D46) - 0.5)
    # Cc — ember afterglow on a SECOND sparser arc set (its own geometry):
    # ghost welds that only ignite in the clearcoat at raking angles
    dist2 = _tempered_dawn_arcs(h, w, s ^ 0x7D50, 320, 5, 10)
    ember = np.exp(-dist2 / (4.5 * sr)).astype(np.float32)
    embpin = np.exp(-((dist2 / (1.1 * sr)) ** 2)).astype(np.float32)
    slow = _msc(h, w, [max(23, int(83 * sr)), max(47, int(191 * sr))], s ^ 0x7D52)
    Cc = 30.0 + 145.0 * ember + 55.0 * embpin + 38.0 * (slow - 0.5)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_tempered_dawn(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_7, seed)
    sr = float(max(h, w)) / 1024.0
    heat, bead = _tempered_dawn_fields(h, w, s)
    hatch = _tempered_dawn_hatch(h, w, s ^ 0x7D30)
    # quantized temper orders at thread scale (straw->bronze->violet->blue)
    # slow th decay pushes the colour orders OUTSIDE the silver bead, so the
    # straw->magenta->cyan->green temper sequence shows around every arc
    film = interference_palette(heat ** 0.55, orders=2.6, quantize=0.80, brightness=0.90)
    ti = (0.36 + hatch * 0.30)[:, :, None] * np.array([1.02, 0.98, 0.92], np.float32)
    presw = np.clip((heat - 0.10) * 9.0, 0.0, 1.0)[:, :, None]
    # temper colors GLAZE the titanium (grain shows through — keeps the
    # weld-envelope luminance low-contrast, only the thread bands pop)
    eff = ti * (1.0 - presw * 0.62) + film * (0.62 + 0.38 * hatch)[:, :, None] * presw * 0.85
    # raw-flake micro pins in the open titanium (1px sparkle everywhere)
    rngp = np.random.default_rng((s ^ 0x7D34) & 0x7FFFFFFF)
    pins2 = np.clip(cv2.GaussianBlur((rngp.random((h, w)) > 0.996).astype(np.float32),
                                     (0, 0), 0.5) * 3.0, 0.0, 1.0)
    eff = eff + pins2[:, :, None] * 0.14
    beadw = (bead * 0.85)[:, :, None]
    eff = eff * (1.0 - beadw) + np.array([0.88, 0.89, 0.92], np.float32) * beadw
    drift = _msc(h, w, [max(31, int(127 * sr)), max(67, int(283 * sr))], s ^ 0x7D33)
    eff = eff * (0.97 + 0.06 * drift[:, :, None])
    # local-mean equalizer: macro luminance stays a LOW-CONTRAST carrier —
    # only the thread-scale temper bands, beads and hatch carry the design
    gl = eff.mean(axis=2)
    gb = cv2.GaussianBlur(gl, (0, 0), 8.0 * sr) + 1e-4
    gain = np.clip((float(gb.mean()) / gb) ** 0.55, 0.78, 1.28).astype(np.float32)
    eff = np.clip(eff * gain[:, :, None], 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE 8) PULSE ALLOY — micro pulse-ring lattice (CRUSHED-FINE rebuild
# 2026-06-10, owner verdict "blobby -> hundreds of micro pulse-centers, ring
# spacing a few px"): ~620 scattered pulse cores; concentric rings every
# 2.3-4.2px (work grid) with the INTEGER ring order striding a 4-stop OKLCH
# LUT so adjacent rings land on contrasting hues; brushed alloy + flake pins
# between rings; each pulse fades outward (low-contrast radial carrier).
# Spec choreography: M = 1px ring crests of center-set 1; R = its OWN micro
# pulse lattice on DIFFERENT centers — glossy ring corridors cut across the
# hue rings so the live highlight walks the palette; Cc = shimmer ponds +
# micro pins on a THIRD center set. UV-agnostic: everything radial-from-
# many-random-centers.
# ============================================================================
FAB_8 = "fable_pulse_alloy"


def _pulse_alloy_rings(h, w, seed, count, wlo, whi):
    """Nearest-center pulse-ring field -> (ring order, ring frac, owner rand).
    cKDTree candidates via _opt_voro_top2 (workers=-1), fully vectorized."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    m = float(max(h, w))
    yy, xx, _, _ = _coords(h, w)
    cys = rng.uniform(0.0, h, count).astype(np.float32)
    cxs = rng.uniform(0.0, w, count).astype(np.float32)
    wds = (rng.uniform(wlo, whi, count) * (m / 1024.0)).astype(np.float32)
    phs = rng.uniform(0.0, 1.0, count).astype(np.float32)
    orand = rng.random(count).astype(np.float32)
    dsq, _, own = _opt_voro_top2(yy, xx, cys, cxs, k=4)
    ringv = (np.sqrt(dsq) / wds[own] + phs[own]).astype(np.float32)
    ridx = np.floor(ringv).astype(np.float32)
    frac = (ringv - ridx).astype(np.float32)
    return ridx, frac, orand[own].astype(np.float32)


def _spec_fable_pulse_alloy(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_8, seed)
    sr = float(max(h, w)) / 1024.0
    yy, xx, _, _ = _coords(h, w)
    ridx, frac, _orand = _pulse_alloy_rings(h, w, s ^ 0x8A10, 620, 2.3, 4.2)
    pulse = (0.18 + 0.82 * np.exp(-ridx * 0.13)).astype(np.float32)
    crest = (np.exp(-((frac - 0.20) / 0.085) ** 2) * pulse).astype(np.float32)
    # R — its OWN micro pulse lattice (different centers AND spacing): the
    # glossy ring corridors crossing set-1's hue rings = hue-travel highlight
    _r2, frac2, _o2 = _pulse_alloy_rings(h, w, s ^ 0x8B20, 380, 3.0, 5.6)
    lane = np.exp(-((frac2 - 0.5) / 0.16) ** 2).astype(np.float32)
    # Cc — shimmer ponds + micro pins on a THIRD center set
    rng3 = np.random.default_rng((s ^ 0x8C30) & 0x7FFFFFFF)
    glow = np.zeros((h, w), np.float32)
    for _i in range(380):
        cy = rng3.uniform(0.0, h)
        cx = rng3.uniform(0.0, w)
        reach = rng3.uniform(2.2, 8.0) * sr
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, 3.2 * reach)
        d2l = (yy[y0:y1, x0:x1] - cy) ** 2 + (xx[y0:y1, x0:x1] - cx) ** 2
        glow[y0:y1, x0:x1] += (np.exp(-d2l / (2.0 * reach * reach)).astype(np.float32)
                               * rng3.uniform(0.5, 1.0))
    glow = np.clip(glow, 0.0, 1.0)
    pinc = np.clip(cv2.GaussianBlur((rng3.random((h, w)) > 0.997).astype(np.float32),
                                    (0, 0), 0.5) * 3.0, 0.0, 1.0)
    glint = _msc(h, w, [2, 4], s ^ 0x8A50)
    slow = _msc(h, w, [max(19, int(52 * sr)), max(43, int(121 * sr))], s ^ 0x8A52)
    M = 24.0 + 204.0 * crest + 22.0 * glint
    R = 176.0 - 132.0 * lane + 22.0 * (_msc(h, w, [2, 5], s ^ 0x8A51) - 0.5) - 14.0 * crest
    Cc = 36.0 + 138.0 * glow + 52.0 * pinc + 28.0 * (slow - 0.5)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_pulse_alloy(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_8, seed)
    sr = float(max(h, w)) / 1024.0
    ridx, frac, orand = _pulse_alloy_rings(h, w, s ^ 0x8A10, 620, 2.3, 4.2)
    # stride the quantized OKLCH LUT so adjacent ring orders land on
    # CONTRASTING hues (full palette around every pulse core)
    t = np.mod(ridx * 3.0 + np.floor(orand * 5.0), 11.0) / 10.0
    cols = _opt_oklch_ramp([(0.00, 0.42, 0.47), (0.14, 0.22, 0.84),
                            (0.78, 0.10, 0.56), (0.99, 0.63, 0.12)],
                           t, flatten_lightness=0.45)
    pulse = (0.18 + 0.82 * np.exp(-ridx * 0.13)).astype(np.float32)
    band = (np.clip((0.62 - frac) * 4.2, 0.0, 1.0) * pulse).astype(np.float32)
    grain = _msc(h, w, [2, 4, 9], s ^ 0x8A30)
    alloy = (0.24 + grain * 0.24)[:, :, None] * np.array([0.965, 0.985, 1.03], np.float32)
    bw = band[:, :, None]
    eff = alloy * (1.0 - bw) + cols * bw
    rngf = np.random.default_rng((s ^ 0x8A31) & 0x7FFFFFFF)
    fl = np.clip(cv2.GaussianBlur((rngf.random((h, w)) > 0.998).astype(np.float32),
                                  (0, 0), 0.5) * 3.0, 0.0, 1.0)
    eff = np.clip(eff + fl[:, :, None] * 0.22, 0.0, 1.0)
    drift = _msc(h, w, [max(29, int(113 * sr)), max(61, int(257 * sr))], s ^ 0x8A40)
    eff = np.clip(eff * (0.90 + 0.20 * drift[:, :, None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# ===== FABLE: SOVEREIGN FLIP (FAB_11) — CRUSHED-FINE rebuild 2026-06-10 =====
# Owner verdict: "blobby -> tri_partition cells MUCH finer (thousands at the
# work grid; soften small) so the 3-phase flip happens at FLAKE scale."
# ~16000 scattered Voronoi cells (≈9px work / 18px canvas) 3-color the car
# into matte-oxblood, mirror-champagne and glass-emerald candy micro
# territories — three sun geometries interleaved like flake. Thin cloisonné
# ink seams trace every cell border (a dense fine web at this cell count).
# Spec: M = champagne mask + flake pins, R = its own 3-band micro grain only
# re-biased per territory, Cc = emerald mask pooled by FLAKE-scale relief +
# varnish lines on emerald seams. Decorrelation by construction.
# ============================================================================
FAB_11 = "fable_sovereign_flip"


def _sovereign_flip_tri(h, w, seed, cells):
    """tri_partition at HALF grid (quarter cell count = same physical cell
    size) then linear-upscaled + renormalised: identical look at ~1/4 the
    KD cost — keeps the 16k-cell flake field inside the 1s perf doctrine."""
    h2, w2 = max(64, h // 2), max(64, w // 2)
    # SAME cell count at half grid = same PHYSICAL flake size, 1/4 the queries
    masks = tri_partition((h2, w2), seed, cells=cells, soften_px=0.45)
    up = [cv2.resize(mk, (w, h), interpolation=cv2.INTER_LINEAR) for mk in masks]
    tot = up[0] + up[1] + up[2] + 1e-6
    return tuple((mk / tot).astype(np.float32) for mk in up)


@_memo_fields
def _sovereign_flip_fields(h, w, seed):
    m = float(max(h, w))
    sr = m / 1024.0
    # FLAKE-SCALE three-phase territory map (area-true cell density)
    cells = max(2500, int(round(20000.0 * (h * w) / (1024.0 * 1024.0))))
    m0, m1, m2 = _sovereign_flip_tri(h, w, (seed ^ 0x3A5C7E) & 0x7FFFFFFF, cells)
    # R's own micro grain (3 tight bands, 2-13px work)
    grain = _msc(h, w, [2, max(3, int(5 * sr)), max(7, int(13 * sr))],
                 seed ^ 0x9B8A7C).astype(np.float32)
    # champagne flake glitter (sharp micro pins, own seed)
    frng = np.random.default_rng((seed ^ 0x5D6E7F) & 0x7FFFFFFF)
    fl = frng.random((h, w)).astype(np.float32)
    flake = np.clip(cv2.GaussianBlur((fl > 0.978).astype(np.float32),
                                     (0, 0), max(0.4, 0.5 * sr)) * 3.2, 0.0, 1.0)
    # emerald glass relief — now FLAKE-scale pooling (2-9px work)
    relief = _msc(h, w, [max(2, int(4 * sr)), max(4, int(9 * sr)), max(11, int(23 * sr))],
                  seed ^ 0x2C4D6F).astype(np.float32)
    # macro tone drift (low-contrast carrier) + cloisonné border ink web
    drift = _msc(h, w, [max(43, int(151 * sr)), max(89, int(307 * sr))],
                 seed ^ 0x8F9EAD).astype(np.float32)
    border = np.clip(_edge(m0, 5.0) + _edge(m1, 5.0) + _edge(m2, 5.0), 0.0, 1.0).astype(np.float32)
    return m0, m1, m2, grain, flake, relief, drift, border


def _spec_fable_sovereign_flip(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_11, seed)
    m0, m1, m2, grain, flake, relief, drift, border = _sovereign_flip_fields(h, w, s)
    g1 = np.random.default_rng((s ^ 0x6F00D5) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    # M — PRIMARY: the champagne micro-territory is a mirror; flake pins
    # overdrive it to full flare. Oxblood + emerald stay metal-dead.
    M = 24.0 + 212.0 * m1 * (0.74 + 0.26 * flake) + 10.0 * (g1 - 0.5)
    # R — PRIMARY: its own 3-band micro grain; territories only re-bias it
    # (oxblood matte-high, champagne tightened, emerald mid-wet).
    R = 62.0 + 148.0 * grain + 34.0 * m0 - 30.0 * m1 - 8.0 * m2
    # Cc — PRIMARY: the emerald glass cells; FLAKE-scale relief pools the wet
    # depth, and the ink seams around emerald cells catch a varnish line.
    Cc = 46.0 + 188.0 * m2 * (0.45 + 0.55 * relief) + 22.0 * (drift - 0.5) + 26.0 * border * m2
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_sovereign_flip(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_11, seed)
    m0, m1, m2, grain, flake, relief, drift, border = _sovereign_flip_fields(h, w, s)
    # oxblood: matte diffuse micro-velvet (OKLab keeps the red deep)
    ox = _opt_oklch_ramp([(0.140, 0.030, 0.045), (0.300, 0.065, 0.085), (0.460, 0.115, 0.115)],
                         np.clip(0.14 + 0.62 * grain + 0.20 * (drift - 0.5), 0.0, 1.0),
                         flatten_lightness=0.15)
    # champagne: SUBDUED warm metal albedo (the flare lives in the SPEC — a
    # true flip reads near-uniform head-on) with sharp flake glitter
    ch = _opt_oklch_ramp([(0.280, 0.220, 0.140), (0.420, 0.360, 0.260), (0.600, 0.540, 0.420)],
                         np.clip(0.30 + 0.30 * grain + 0.55 * flake, 0.0, 1.0))
    # emerald: TRUE Beer-Lambert candy pooling at FLAKE scale (depth tuned so
    # all three territory mean-grays sit within ~0.05 — head-on the mosaic is
    # near-uniform; the three SPEC geometries do the flipping)
    emetal = _opt_oklch_ramp([(0.62, 0.78, 0.66), (0.88, 0.97, 0.88)], grain)
    em = candy_absorb(emetal, (0.030, 0.420, 0.200), 0.40 + 1.20 * (1.0 - relief), density=1.0)
    eff = ox * m0[..., None] + ch * m1[..., None] + em * m2[..., None]
    eff = eff * (0.90 + 0.20 * drift)[..., None]
    # cloisonné ink seams between micro-territories (dense stained-glass web)
    eff = eff * (1.0 - 0.60 * border[..., None])
    # local-mean equalizer: same-color cell CLUSTERS otherwise merge into
    # macro luminance blobs — flatten them so the flip stays at flake scale
    sr2 = float(max(h, w)) / 1024.0
    gl = eff.mean(axis=2)
    gb = cv2.GaussianBlur(gl, (0, 0), 8.0 * sr2) + 1e-4
    gain = np.clip((float(gb.mean()) / gb) ** 0.74, 0.72, 1.38).astype(np.float32)
    eff = np.clip(eff * gain[..., None], 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# ===== FABLE: STATIC BLOOM (FAB_12) — CRUSHED-FINE rebuild 2026-06-10 =======
# Owner verdict: "blobby -> micro-static: territory cells ~6-16px, each
# territory's motif at 2-6px grain." Territories are now the one-hot argmax
# of three independent blurred noise fields (organic interlocking micro
# islands ~12-16px at canvas — NOT a Voronoi; FAB_11 owns tri_partition).
# Motifs per territory, all at 2-6px canvas grain: electric-cobalt micro-dot
# static, magenta micro-filament streaks on three random axes, and ~1500
# amber micro-embers. Each spec channel reads EXACTLY ONE territory's motif
# (M=static pins, R=filament gloss lanes, Cc=ember glow) — decorrelation by
# construction. UV-agnostic: isotropic islands, random axes, scattered embers.
# ============================================================================
FAB_12 = "fable_static_bloom"


def _static_bloom_territories(h, w, seed, sigma):
    """Micro territory map: one-hot argmax of three independent blurred noise
    fields -> organic interlocking islands (~3-4*sigma px across)."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    f0 = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32), (0, 0), sigma)
    f1 = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32), (0, 0), sigma)
    f2 = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32), (0, 0), sigma)
    am = np.argmax(np.stack([f0, f1, f2], axis=0), axis=0)
    masks = [cv2.GaussianBlur((am == c).astype(np.float32), (0, 0), 0.5) for c in range(3)]
    tot = masks[0] + masks[1] + masks[2] + 1e-6
    return tuple((mk / tot).astype(np.float32) for mk in masks)


def _static_bloom_fields(h, w, seed):
    m = float(max(h, w))
    sr = m / 1024.0
    m0, m1, m2 = _static_bloom_territories(h, w, (seed ^ 0x77E1A2) & 0x7FFFFFFF,
                                           max(1.4, 2.4 * sr))
    yy, xx, _, _ = _coords(h, w)
    # --- motif 0: micro-dot static (~1px work dots), density drifting
    rng0 = np.random.default_rng((seed ^ 0x88F2B3) & 0x7FFFFFFF)
    base = rng0.random((h, w)).astype(np.float32)
    dens = _msc(h, w, [max(17, int(61 * sr)), max(43, int(151 * sr))],
                seed ^ 0x99A3C4).astype(np.float32)
    d_small = (base > (0.945 - 0.035 * dens)).astype(np.float32)
    dots = np.clip(cv2.GaussianBlur(d_small, (0, 0), max(0.4, 0.5 * sr)) * 2.8,
                   0.0, 1.0).astype(np.float32)
    # --- motif 1: micro filament streaks — thin warped ridges on THREE axes
    rng1 = np.random.default_rng((seed ^ 0xAAB4D5) & 0x7FFFFFFF)
    wpx = (_msc(h, w, [max(5, int(17 * sr)), max(13, int(47 * sr))],
                seed ^ 0xBBC5E6) - 0.5) * (9.0 * sr)
    fil = np.zeros((h, w), np.float32)
    for _ in range(3):
        ang = rng1.uniform(0.0, np.pi)
        per = max(2.2, rng1.uniform(2.5, 4.0) * sr)
        ph = (xx * np.cos(ang) + yy * np.sin(ang) + wpx * rng1.uniform(0.6, 1.2)) / per
        ridge = 1.0 - np.abs(np.sin(np.pi * ph))
        fil = np.maximum(fil, ridge ** 3.5)
    fil = fil.astype(np.float32)
    # --- motif 2: ~1500 amber micro-embers (1.2-3.2px sigma, local windows)
    rng2 = np.random.default_rng((seed ^ 0xCCD6F7) & 0x7FFFFFFF)
    bloom = np.zeros((h, w), np.float32)
    for _ in range(2200):  # scatter placement loop (tiny local windows)
        cy = rng2.uniform(0.0, h)
        cx = rng2.uniform(0.0, w)
        rad = max(1.0, rng2.uniform(1.2, 3.0) * sr)
        amp = rng2.uniform(0.45, 1.0)
        y0, y1, x0, x1 = _opt_win(h, w, cy, cx, 3.0 * rad)
        d2l = (yy[y0:y1, x0:x1] - cy) ** 2 + (xx[y0:y1, x0:x1] - cx) ** 2
        bloom[y0:y1, x0:x1] += amp * np.exp(-d2l / (2.0 * rad * rad))
    bloom = np.clip(bloom, 0.0, 1.0).astype(np.float32)
    return m0, m1, m2, dots, fil, bloom, dens


def _spec_fable_static_bloom(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_12, seed)
    m0, m1, m2, dots, fil, bloom, dens = _static_bloom_fields(h, w, s)
    g1 = np.random.default_rng((s ^ 0x10F0A1) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    g2 = np.random.default_rng((s ^ 0x20E1B2) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    g3 = np.random.default_rng((s ^ 0x30D2C3) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    sr = max(h, w) / 1024.0
    cmac = _msc(h, w, [max(37, int(131 * sr)), max(83, int(293 * sr))],
                s ^ 0x40C3D4).astype(np.float32)
    # M — reads ONLY the static territory: every micro dot is a mirror pin.
    M = 28.0 + 210.0 * dots * m0 + 12.0 * (g1 - 0.5)
    # R — reads ONLY the filament territory: micro gloss lanes cut the matte.
    R = 168.0 - 128.0 * fil * m1 + 20.0 * (g2 - 0.5)
    # Cc — reads ONLY the ember territory: glow pools in the micro-embers,
    # with its own slow macro breath everywhere else.
    Cc = 46.0 + 188.0 * bloom * m2 + 18.0 * (cmac - 0.5) + 12.0 * (g3 - 0.5)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_static_bloom(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_12, seed)
    sr = max(h, w) / 1024.0
    m0, m1, m2, dots, fil, bloom, dens = _static_bloom_fields(h, w, s)
    # territory 0 — electric cobalt static: bright cyan pins on deep blue
    col0 = _opt_oklch_ramp([(0.030, 0.070, 0.220), (0.070, 0.220, 0.500), (0.350, 0.850, 1.000)],
                           np.clip(0.16 + 0.62 * dots + 0.22 * (dens - 0.5), 0.0, 1.0),
                           flatten_lightness=0.1)
    # territory 1 — magenta micro-filaments burning through dark plum
    col1 = _opt_oklch_ramp([(0.160, 0.030, 0.140), (0.450, 0.080, 0.420), (0.950, 0.450, 0.850)],
                           np.clip(0.14 + 0.74 * fil, 0.0, 1.0), flatten_lightness=0.1)
    # territory 2 — amber micro-embers glowing out of deep maroon
    col2 = _opt_oklch_ramp([(0.200, 0.060, 0.040), (0.650, 0.280, 0.100), (1.000, 0.750, 0.400)],
                           np.clip(0.12 + 0.80 * bloom, 0.0, 1.0), flatten_lightness=0.1)
    eff = col0 * m0[..., None] + col1 * m1[..., None] + col2 * m2[..., None]
    # mid-band island shimmer + macro dens drift: low-contrast carriers so the
    # micro-static still reads at car distance
    isl = _msc(h, w, [max(4, int(6 * sr)), max(9, int(13 * sr))], s ^ 0x55AA66)
    # island luminance tiers (cobalt deepest, amber brightest) — the carrier
    # that keeps the micro-static readable at car distance
    tier = (0.84 + 0.24 * m2 + 0.10 * m1).astype(np.float32)
    eff = np.clip(eff * ((0.78 + 0.24 * dens + 0.16 * isl) * tier)[..., None],
                  0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE #13 — AURORA TRAVEL (fable_aurora_travel) — FINE-DETAIL rebuild
# 2026-06-10. Owner verdict: "CLOSE but needs 2-3x more fine details" — same
# concept + teal->violet->magenta OKLCH hue-travel palette, but curtain
# widths HALVED (lam 10-20), NEW flake-scale aurora RAY striations along each
# curtain's normal (2-3.4px work period, breathing amplitude), sharper/finer
# curtain-edge filaments, DENSER glossy R corridors (5 jittered crossing
# axes) and smaller, denser shimmer ponds. The live highlight still migrates
# ACROSS hues as the car rotates. UV-agnostic: 4 random curtain axes +
# isotropic warp; rays/corridors on per-axis jitter; ponds at random centers.
# ============================================================================
FAB_13 = "fable_aurora_travel"


@_memo_fields
def _aurora_travel_fields(h, w, seed):
    """flow (hue key), rays (signed micro striations), filaments (M),
    corridors (R), pools (Cc) — HxW float32."""
    m = float(max(h, w))
    sr = m / 1024.0
    yy, xx, _, _ = _coords(h, w)

    # flow: 4 random-axis warped sine curtains at HALF the round-1 widths
    rng_f = np.random.default_rng(seed ^ 0x13A001)
    axes = [float(rng_f.uniform(0.0, np.pi)) for _ in range(4)]
    warp = _msc(h, w, [max(int(m * 0.015), 3), max(int(m * 0.06), 7), max(int(m * 0.16), 11)],
                seed ^ 0x13B002) - 0.5
    flow = np.zeros((h, w), np.float32)
    for ang in axes:
        u = (float(np.cos(ang)) * xx + float(np.sin(ang)) * yy) / m
        lam = float(rng_f.uniform(14.0, 26.0))
        ph = float(rng_f.uniform(0.0, 2.0 * np.pi))
        amp = float(rng_f.uniform(0.6, 1.1))
        flow += amp * np.sin(2.0 * np.pi * lam * (u + 0.17 * warp) + ph)
    flow -= flow.min()
    flow /= max(float(flow.max()), 1e-6)
    ripple = _msc(h, w, [3, max(int(m * 0.009), 4)], seed ^ 0x13C003)
    flow = np.clip(0.80 * flow + 0.20 * ripple, 0.0, 1.0).astype(np.float32)

    # rays: flake-scale aurora striations along each curtain's NORMAL
    # (2-3.4px work period), amplitude breathing through its own gate field
    rng_y = np.random.default_rng(seed ^ 0x13A902)
    rays = np.zeros((h, w), np.float32)
    gates = [_msc(h, w, [max(int(m * 0.02), 4), max(int(m * 0.07), 7)],
                  (seed ^ 0x13AA13) + 5 * k) for k in range(2)]
    for k in range(3):
        ang = axes[k] + 0.5 * np.pi
        per = max(2.2, float(rng_y.uniform(2.4, 3.4)) * sr)
        u = (float(np.cos(ang)) * xx + float(np.sin(ang)) * yy) / per
        rays += (np.sin(2.0 * np.pi * u + float(rng_y.uniform(0.0, 6.283))
                        + warp * float(rng_y.uniform(4.0, 9.0)))
                 * np.clip((gates[k % 2] - 0.30) * 2.0, 0.0, 1.0))
    rays = (rays / 3.0).astype(np.float32)

    # filaments: sharpened curtain edges + micro streamers (M primary)
    fil = _edge(flow, gain=m * 0.06)
    fil = np.clip(fil ** 1.4 * 2.0, 0.0, 1.0)
    streamers = _msc(h, w, [2, max(int(m * 0.005), 3), max(int(m * 0.015), 4)], seed ^ 0x13D004)
    fil = np.clip(fil * (0.55 + 0.45 * streamers) + 0.32 * (streamers > 0.92),
                  0.0, 1.0).astype(np.float32)

    # corridors: DENSER glossy lanes crossing the curtain axes — 5 jittered
    # axes, own wavelengths/phases/warp = R's own primary geometry
    rng_r = np.random.default_rng(seed ^ 0x13E005)
    warp_r = _msc(h, w, [max(int(m * 0.02), 4), max(int(m * 0.08), 8)], seed ^ 0x13F006) - 0.5
    lanes = np.zeros((h, w), np.float32)
    for k in range(5):
        ang = axes[k % 4] + 0.5 * np.pi + float(rng_r.uniform(-0.35, 0.35))
        u = (float(np.cos(ang)) * xx + float(np.sin(ang)) * yy) / m
        lam = float(rng_r.uniform(7.0, 14.0))
        ph = float(rng_r.uniform(0.0, 2.0 * np.pi))
        sv = 0.5 + 0.5 * np.sin(2.0 * np.pi * lam * (u + 0.22 * warp_r) + ph)
        lane = np.clip((sv - 0.78) / 0.09, 0.0, 1.0)
        lanes = np.maximum(lanes, (lane * lane * (3.0 - 2.0 * lane)).astype(np.float32))

    # pools: smaller, denser shimmer ponds + slow drift (Cc primary)
    def _aurora_travel_pond(acc, yy2, xx2, cy, cx, rad, ang2, amp):
        rr = max(0.22 * rad, 1.6)
        d2l = (yy2 - cy) ** 2 + (xx2 - cx) ** 2
        acc += amp * np.exp(-d2l / (2.0 * rr * rr))

    ponds = _opt_scatter_field(h, w, seed ^ 0x130907, 280, _aurora_travel_pond,
                               lambda rad: 3.2 * max(0.22 * rad, 1.6))
    ponds /= max(float(ponds.max()), 1e-6)
    ponds = ponds.astype(np.float32)
    drift = _msc(h, w, [max(int(m * 0.10), 9), max(int(m * 0.26), 15)], seed ^ 0x131A08)
    pools = np.clip(0.66 * ponds + 0.34 * drift, 0.0, 1.0).astype(np.float32)
    return flow, rays, fil, lanes, ponds, pools


def _spec_fable_aurora_travel(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_13, seed)
    flow, rays, fil, lanes, ponds, pools = _aurora_travel_fields(h, w, s)
    m = float(max(h, w))
    micro_m = _msc(h, w, [2, max(int(m * 0.006), 3)], s ^ 0x13AB10)
    micro_r = _msc(h, w, [3, max(int(m * 0.009), 4)], s ^ 0x13BC11)
    micro_c = _msc(h, w, [2, max(int(m * 0.005), 3)], s ^ 0x13CD12)
    # M: curtain filaments flare; ray striations twinkle the metallic
    M = 22.0 + 188.0 * fil + 24.0 * micro_m + 26.0 * np.clip(rays, 0.0, 1.0)
    # R: dense mirror corridors cut ACROSS the hue bands — the highlight
    # physically walks teal->violet->magenta as the car rotates
    R = 182.0 - 142.0 * lanes + 24.0 * micro_r - 10.0 * fil
    # Cc: micro shimmer ponds glow wet + pin sparkle
    Cc = 50.0 + 158.0 * pools + 26.0 * (micro_c > 0.88).astype(np.float32) + 10.0 * micro_c
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_aurora_travel(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_13, seed)
    flow, rays, fil, lanes, ponds, pools = _aurora_travel_fields(h, w, s)
    m = float(max(h, w))
    # OKLCH hue-travel ramp: teal -> violet -> magenta at even lightness
    # gray-mean-balanced stops (same teal/violet/magenta hues; equalised RGB
    # means so the macro curtains carry CHROMA, not luminance blobs)
    stops = [(0.03, 0.60, 0.56), (0.31, 0.17, 0.68), (0.70, 0.10, 0.46)]
    eff = _opt_oklch_ramp(stops, flow, flatten_lightness=0.78)
    lin = srgb_to_linear(eff)
    lin = lin * (1.0 + 0.45 * rays)[:, :, None]            # flake-scale ray striations
    lin = lin + (fil ** 1.3)[:, :, None] * np.array([0.26, 0.40, 0.48], np.float32)
    lin = lin * (1.0 - 0.22 * ponds[:, :, None])           # ponds deepen into night
    # (pond-ONLY darkening: the slow Cc drift stays out of the albedo)
    eff = linear_to_srgb(np.clip(lin, 0.0, 1.0))
    grain = _msc(h, w, [2, max(int(m * 0.004), 2)], s ^ 0x13DE13)
    eff = eff * (0.93 + 0.12 * grain[:, :, None])
    # local-mean equalizer: the curtain macro stays a low-contrast CHROMA
    # carrier; rays/filaments/ripple own the luminance story
    sr2 = m / 1024.0
    gl = eff.mean(axis=2)
    gb = cv2.GaussianBlur(gl, (0, 0), 10.0 * sr2) + 1e-4
    gain = np.clip((float(gb.mean()) / gb) ** 0.60, 0.78, 1.28).astype(np.float32)
    # 0.84 master dim: keeps the aurora rich (the flattened ramp + equalizer
    # otherwise wash the night-sky body toward pale lavender)
    eff = np.clip(eff * gain[:, :, None] * 0.84, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE #19 - MAGNETITE FLOW (fable_magnetite_flow) - CRUSHED-FINE REBUILD
# Owner verdict: "4-5x more finer detail more coloring in spec to make it
# pop." The spike lattice is now MICRO SPIKE-FUR covering the whole car:
# 150 scattered magnetic domains (Voronoi-owned), each combing its own
# 3-wave hex interference fur at ~4-7px work-grid pitch (spike tips 2-3px at
# 2048), separated by thin wet seams. Steel-blue Beer-Lambert candy pools
# between every spike. SPEC POP: the three channels ride loud, separate
# geometries - M = red-hot spike tips, R = green flow-aligned scanline lanes
# (each domain combs its own direction), Cc = blue condensation droplets -
# so the channel composite reads vividly multi-hue.
# ============================================================================
FAB_19 = "fable_magnetite_flow"


def _magnetite_flow_fields(h, w, seed):
    """Domain-owned hex spike fur + flow streak + droplets + gleam carrier."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    px = m / 1024.0
    nd_ = 150
    cys = rng.uniform(0, h, nd_).astype(np.float32)
    cxs = rng.uniform(0, w, nd_).astype(np.float32)
    angs = rng.uniform(0.0, 2.0 * np.pi, nd_).astype(np.float32)
    pits = (rng.uniform(4.2, 6.6, nd_) * px).astype(np.float32)
    phs = rng.uniform(0.0, 2.0 * np.pi, (nd_, 3)).astype(np.float32)
    damp = rng.uniform(0.80, 1.0, nd_).astype(np.float32)
    d1, d2, own = _opt_voro_top2(yy, xx, cys, cxs, k=4)
    d1 = np.sqrt(d1)
    d2 = np.sqrt(d2)
    seam = np.exp(-(((d2 - d1) / max(1.6 * px, 1.2)) ** 2)).astype(np.float32)
    wamt = 1.5 * px
    wx = (_msc(h, w, [5, 13], seed ^ 0x19A5) - 0.5) * 2.0 * wamt
    wy = (_msc(h, w, [5, 13], seed ^ 0x19B6) - 0.5) * 2.0 * wamt
    dxw = (xx - cxs[own]) + wx
    dyw = (yy - cys[own]) + wy
    A = angs[own]
    K = (2.0 * np.pi) / pits[own]
    f = np.zeros((h, w), np.float32)
    for j in range(3):
        aj = A + j * (2.0 * np.pi / 3.0)
        f += np.cos((dxw * np.cos(aj) + dyw * np.sin(aj)) * K + phs[own, j])
    f *= (1.0 / 3.0)
    dome = (1.0 - 0.85 * seam) * damp[own]
    tips = ((np.clip(f, 0.0, 1.0) ** 8) * dome).astype(np.float32)
    relief = ((np.clip((f + 1.0) * 0.5, 0.0, 1.0) ** 1.6) * dome).astype(np.float32)
    # flow-aligned wet scanline streak (R primary): each domain combs its own
    # direction; warp keeps it organic
    warp = (_msc(h, w, [9, 21], seed ^ 0x19E5) - 0.5) * 2.0
    v = dyw * np.cos(A) - dxw * np.sin(A)
    streak = (0.5 + 0.5 * np.sin(v * (2.0 * np.pi) / max(3.4 * px, 2.0) + warp * 4.6)).astype(np.float32)
    # condensation droplets (Cc primary): own micro field
    dn = _msc(h, w, [2, 4], seed ^ 0x19F6)
    drop = np.clip((dn - 0.88) / 0.12, 0.0, 1.0)
    droplets = np.clip(cv2.GaussianBlur(drop, (0, 0), max(1.1 * px, 0.8)) * 2.6, 0.0, 1.0).astype(np.float32)
    gleam = _msc(h, w, [max(int(m * 0.025), 5), max(int(m * 0.07), 9)], seed ^ 0x190A)
    return tips, relief, seam, streak, droplets, gleam


def _spec_fable_magnetite_flow(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_19, seed)
    tips, relief, seam, streak, droplets, gleam = _magnetite_flow_fields(h, w, s)
    micro = _msc(h, w, [2, 3], s ^ 0x1901)
    mr = _msc(h, w, [3, 7], s ^ 0x1912)
    # LOUD channel separation (owner: make the spec pop): M = hot spike tips,
    # R = full-swing flow lanes, Cc = droplets + gleam - a multi-hue composite.
    M = 16.0 + 234.0 * tips + 16.0 * (micro > 0.93).astype(np.float32)
    R = 40.0 + 178.0 * streak + 18.0 * (mr - 0.5)
    Cc = 26.0 + 168.0 * droplets + 44.0 * gleam - 30.0 * seam
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_magnetite_flow(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_19, seed)
    tips, relief, seam, streak, droplets, gleam = _magnetite_flow_fields(h, w, s)
    flow = np.clip(0.16 + 0.68 * relief + 0.14 * (streak - 0.5), 0.0, 1.0)
    metal = _opt_oklch_ramp([(0.235, 0.285, 0.365), (0.45, 0.54, 0.66),
                             (0.86, 0.91, 0.97)], flow)
    # Beer-Lambert: the dark coat pools deep between every micro spike and at
    # the domain seams, thins to bright steel at the crests
    depth = np.clip(1.30 - 1.10 * relief + 0.30 * seam - 0.22 * gleam, 0.0, 2.2)
    eff = candy_absorb(metal, np.array([0.30, 0.38, 0.55], np.float32), depth)
    eff = eff + (tips * (0.55 + 0.45 * gleam))[:, :, None] * np.array([0.70, 0.80, 0.95], np.float32) * 0.32
    eff = eff + droplets[:, :, None] * np.array([0.05, 0.08, 0.16], np.float32) * 0.5
    eff = np.clip(eff, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE #15 - QUICKSILVER GARDEN (fable_quicksilver_garden) - CRUSHED REBUILD
# Owner verdict: "really like the idea and the hot outlines in the spec...
# needs about 5x smaller/finer." KEPT: the white-hot mirror rim outlines (M)
# and the per-cell pastel-garden identity. REBUILT: 120 cells -> 3200 micro
# cells (~18px work grid ~= 36px at 2048, rims ~2px at 2048), and every micro
# cell now carries RAMP DETAIL inside it: its own oriented pastel mini-ramp
# PLUS micro striation bands (~5px at 2048) that also drive the candy depth.
# Spec: M = hot rim web (the keeper idea, now 26x denser), R = per-cell gloss
# mosaic (3200 independent rolls), Cc = per-cell core pooling choreography.
# ============================================================================
FAB_15 = "fable_quicksilver_garden"

_quicksilver_garden_cache = {}


def _quicksilver_garden_fields(h, w, seed):
    """(tcell, interior, rim, band, core, owner, n) micro-garden geometry."""
    key = (int(h), int(w), int(seed))
    hit = _quicksilver_garden_cache.get(key)
    if hit is not None:
        return hit
    m = float(max(h, w))
    yy, xx, _, _ = _coords(h, w)
    n = 5200
    rng = np.random.default_rng((seed ^ 0x15A001) & 0x7FFFFFFF)
    sy = rng.uniform(0, h, n).astype(np.float32)
    sx = rng.uniform(0, w, n).astype(np.float32)
    cang = rng.uniform(0.0, 2.0 * np.pi, n).astype(np.float32)
    crad = (np.sqrt(h * w / float(n)) * rng.uniform(0.75, 1.30, n)).astype(np.float32)
    toff = rng.uniform(0.0, 0.62, n).astype(np.float32)
    nb = rng.integers(2, 5, n).astype(np.float32)
    wy = (_msc(h, w, [max(int(m * 0.008), 3), max(int(m * 0.03), 5)], seed ^ 0x15B002) - 0.5) * (m * 0.012)
    wx = (_msc(h, w, [max(int(m * 0.008), 3), max(int(m * 0.03), 5)], seed ^ 0x15C003) - 0.5) * (m * 0.012)
    yyw = yy + wy
    xxw = xx + wx
    d1, d2, owner = _opt_voro_top2(yyw, xxw, sy, sx)
    d1 = np.sqrt(d1)
    d2 = np.sqrt(d2)
    border = d2 - d1
    rim = np.exp(-((border / max(m * 0.0009, 0.8)) ** 2)).astype(np.float32)
    interior = np.clip(border / (m * 0.0045), 0.0, 1.0)
    interior = (interior * interior * (3.0 - 2.0 * interior)).astype(np.float32)
    am = cang[owner]
    rm = np.maximum(crad[owner], 1.0)
    proj = ((xxw - sx[owner]) * np.cos(am) + (yyw - sy[owner]) * np.sin(am)) / rm
    tcell = np.clip(toff[owner] + 0.38 * np.clip(0.5 + 0.5 * proj, 0.0, 1.0), 0.0, 1.0).astype(np.float32)
    band = (0.5 + 0.5 * np.cos(np.pi * 5.5 * nb[owner] * proj)).astype(np.float32)
    core = np.clip(1.0 - d1 / rm, 0.0, 1.0).astype(np.float32)
    out = (tcell, interior, rim, band, core, owner, n)
    if len(_quicksilver_garden_cache) >= 4:
        _quicksilver_garden_cache.pop(next(iter(_quicksilver_garden_cache)))
    _quicksilver_garden_cache[key] = out
    return out


def _spec_fable_quicksilver_garden(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_15, seed)
    tcell, interior, rim, band, core, owner, n = _quicksilver_garden_fields(h, w, s)
    m = float(max(h, w))
    rng = np.random.default_rng((s ^ 0x15D004) & 0x7FFFFFFF)
    rcell = rng.uniform(30.0, 215.0, n).astype(np.float32)   # per-cell gloss roll
    ccamp = rng.uniform(0.35, 1.00, n).astype(np.float32)    # per-cell pool depth
    micro_r = _msc(h, w, [3, max(int(m * 0.008), 3)], s ^ 0x15E005)
    micro_m = _msc(h, w, [2, max(int(m * 0.005), 3)], s ^ 0x15F006)
    slow_c = _msc(h, w, [max(int(m * 0.09), 9), max(int(m * 0.22), 13)], s ^ 0x150A07)
    # R: 3200 cells each roll their OWN roughness - a micro gloss mosaic
    R = rcell[owner] * (0.85 + 0.30 * micro_r)
    # M: the keeper white-hot rim outlines, now a dense micro web + spark pins
    M = 24.0 + 208.0 * (rim ** 0.9) + 26.0 * (micro_m > 0.91).astype(np.float32) + 10.0 * micro_m
    # Cc: wet pooling toward each micro-cell's own center, per-cell depth
    Cc = 40.0 + 158.0 * (core ** 1.4) * ccamp[owner] + 26.0 * slow_c
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_quicksilver_garden(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_15, seed)
    tcell, interior, rim, band, core, owner, n = _quicksilver_garden_fields(h, w, s)
    m = float(max(h, w))
    # liquid chrome bed: FINE caustic luminance + a quiet slow breath
    cff = _msc(h, w, [2, 5], s ^ 0x151B08)
    cfs = _msc(h, w, [max(int(m * 0.06), 7), max(int(m * 0.14), 9)], s ^ 0x152C19)
    cl = 0.38 + 0.42 * cff ** 1.5 + 0.26 * np.clip((cff - 0.84) / 0.08, 0.0, 1.0) + 0.06 * (cfs - 0.5)
    chrome = np.clip(cl[:, :, None] * np.array([0.94, 0.985, 1.05], np.float32), 0.0, 1.0)
    # per-micro-cell pastel mini-ramps along each cell's own orientation
    stops = [(0.58, 0.93, 0.78), (0.55, 0.78, 0.96), (0.78, 0.62, 0.93),
             (0.96, 0.62, 0.72), (0.98, 0.88, 0.55)]
    pastel = _opt_oklch_ramp(stops, tcell, flatten_lightness=0.72)
    # candy depth: interior pooling + micro striation bands = ramp detail
    # INSIDE every micro cell
    depth = (interior * (0.26 + 0.36 * core + 0.30 * band)).astype(np.float32)
    eff = candy_absorb(chrome, pastel, depth, density=1.0)
    # the keeper: white-hot mirror rims outlining every micro cell
    riml = ((rim ** 1.1) * 0.85)[:, :, None]
    eff = eff * (1.0 - riml) + np.array([0.97, 0.985, 1.0], np.float32) * riml
    grain = _msc(h, w, [2, max(int(m * 0.004), 2)], s ^ 0x153D0B)
    eff = np.clip(eff * (0.93 + 0.12 * grain[:, :, None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# ============================================================================
# FABLE #16 - EMBERLINE DRIFT (fable_emberline_drift) - CRUSHED-FINE REBUILD
# Owner verdict: "5-6x more detail. Much finer/smaller design" (floor; pushed
# further). Dune wavelengths cut ~25x from round 1: FIVE interfering folded
# ridge fields (pitch ~5-9px work grid ~= 10-19px at 2048, knife-edge cusps
# 1-2px) make a micro dune lattice, with live EMBER MICRO-SPARKS (1-2px)
# crackling between the crests. Gold->crimson->smoke OKLCH ramp rides the
# dune value; macro is only a low-contrast valley-shade carrier. Spec:
# M = crest caps, R = glossy micro lane threads on their OWN axes, Cc = ember
# glow pools grown from the sparks' own field.
# ============================================================================
FAB_16 = "fable_emberline_drift"


@_memo_fields
def _emberline_drift_fields(h, w, seed):
    """dunes (hue key), crest (M), ember (sparks), lanes (R), glow (Cc)."""
    m = float(max(h, w))
    yy, xx, _, _ = _coords(h, w)
    rng_d = np.random.default_rng((seed ^ 0x16A001) & 0x7FFFFFFF)
    warp = _msc(h, w, [max(int(m * 0.010), 3), max(int(m * 0.035), 5)], seed ^ 0x16B002) - 0.5
    acc = np.zeros((h, w), np.float32)
    wsum = 0.0
    for _ in range(5):
        ang = float(rng_d.uniform(0.0, np.pi))
        u = (float(np.cos(ang)) * xx + float(np.sin(ang)) * yy) / m
        lam = float(rng_d.uniform(110.0, 205.0))     # ridge pitch ~5-9px work
        ph = float(rng_d.uniform(0.0, 2.0 * np.pi))
        wgt = float(rng_d.uniform(0.6, 1.1))
        folded = np.abs(np.sin(2.0 * np.pi * (lam * u + 2.2 * warp) + ph)).astype(np.float32)
        acc += wgt * (1.0 - folded ** 0.7)           # cusped micro ridges
        wsum += wgt
    dunes = acc / max(wsum, 1e-6)
    q_lo = float(np.quantile(dunes, 0.07))
    q_hi = float(np.quantile(dunes, 0.93))
    dunes = np.clip((dunes - q_lo) / max(q_hi - q_lo, 1e-6), 0.0, 1.0).astype(np.float32)
    # crest caps (M primary): thin glinting ridge tips
    q1 = float(np.quantile(dunes, 0.92))
    q2 = float(np.quantile(dunes, 0.985))
    crest = np.clip((dunes - q1) / max(q2 - q1, 1e-5), 0.0, 1.0) ** 1.4
    specks = _msc(h, w, [2, 3], seed ^ 0x16D004)
    crest = np.clip(crest * (0.60 + 0.40 * specks) + 0.30 * (specks > 0.95), 0.0, 1.0).astype(np.float32)
    # ember micro-sparks living BETWEEN the crests
    emn = _msc(h, w, [2, 3], seed ^ 0x16E009)
    ember = (np.clip((emn - 0.955) / 0.045, 0.0, 1.0)
             * np.clip((0.55 - dunes) / 0.30, 0.0, 1.0)).astype(np.float32)
    # glossy micro lane threads on their OWN axes (R primary)
    rng_r = np.random.default_rng((seed ^ 0x16E005) & 0x7FFFFFFF)
    warp_r = _msc(h, w, [max(int(m * 0.012), 3), max(int(m * 0.04), 5)], seed ^ 0x16F006) - 0.5
    lanes = np.zeros((h, w), np.float32)
    for _ in range(3):
        ang = float(rng_r.uniform(0.0, np.pi))
        u = (float(np.cos(ang)) * xx + float(np.sin(ang)) * yy) / m
        lam = float(rng_r.uniform(55.0, 105.0))
        ph = float(rng_r.uniform(0.0, 2.0 * np.pi))
        sv = 0.5 + 0.5 * np.sin(2.0 * np.pi * (lam * u + 1.6 * warp_r) + ph)
        lane = np.clip((sv - 0.78) / 0.10, 0.0, 1.0)
        lanes = np.maximum(lanes, (lane * lane * (3.0 - 2.0 * lane)).astype(np.float32))
    # ember glow pools (Cc primary): grown from the sparks' own field
    glow = cv2.GaussianBlur(ember, (0, 0), max(2.2 * (m / 1024.0), 1.2))
    glow /= max(float(glow.max()), 1e-6)
    glow = np.clip(0.70 * glow + 0.50 * ember, 0.0, 1.0).astype(np.float32)
    macroA = _msc(h, w, [max(int(m * 0.03), 5), max(int(m * 0.08), 9)], seed ^ 0x160A07)
    return dunes, crest, ember, lanes, glow, macroA


def _spec_fable_emberline_drift(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of(FAB_16, seed)
    dunes, crest, ember, lanes, glow, macroA = _emberline_drift_fields(h, w, s)
    m = float(max(h, w))
    micro_m = _msc(h, w, [2, max(int(m * 0.006), 3)], s ^ 0x161B08)
    micro_r = _msc(h, w, [3, max(int(m * 0.009), 4)], s ^ 0x162C09)
    slow_c = _msc(h, w, [max(int(m * 0.09), 9), max(int(m * 0.22), 13)], s ^ 0x163D0A)
    # M: only the knife-edge dune crests catch metal glint
    M = 22.0 + 198.0 * crest + 18.0 * micro_m
    # R: glossy micro lane threads crossing the dunes at their own angles
    R = 188.0 - 142.0 * lanes + 24.0 * micro_r
    # Cc: ember glow pools - the sparks' own halo field + its own slow drift
    Cc = 40.0 + 172.0 * glow + 26.0 * (slow_c - 0.5) + 14.0 * slow_c
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_emberline_drift(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of(FAB_16, seed)
    dunes, crest, ember, lanes, glow, macroA = _emberline_drift_fields(h, w, s)
    m = float(max(h, w))
    # gold->crimson->smoke OKLCH: the micro dune value carries the detail,
    # a slow isotropic drift only opens gentle hue zones (no global axis)
    drift_t = _msc(h, w, [max(int(m * 0.07), 7), max(int(m * 0.18), 11)], s ^ 0x165F0C)
    tkey = np.clip(0.70 * dunes + 0.30 * drift_t, 0.0, 1.0)
    stops = [(0.96, 0.74, 0.20), (0.74, 0.13, 0.10), (0.30, 0.27, 0.29)]
    eff = _opt_oklch_ramp(stops, tkey, flatten_lightness=0.50)
    lin = srgb_to_linear(eff)
    lin = lin + (crest ** 1.2)[:, :, None] * np.array([0.34, 0.22, 0.07], np.float32)
    lin = lin + (ember ** 1.1)[:, :, None] * np.array([0.85, 0.30, 0.05], np.float32) * 0.45
    eff = linear_to_srgb(np.clip(lin, 0.0, 1.0))
    # low-contrast carrier UNDER the detail: valleys shade deeper where the
    # drift-sea runs calm (survives track distance without macro blobs)
    shade = 1.0 - 0.20 * (1.0 - dunes) * (0.35 + 0.65 * (1.0 - macroA))
    eff = eff * shade[:, :, None]
    grain = _msc(h, w, [2, 3], s ^ 0x164E0B)
    eff = np.clip(eff * (0.92 + 0.14 * grain[:, :, None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


FABLE_MONOLITHICS.update({
    FAB_2:  (_spec_fable_glacier_core, _paint_fable_glacier_core),
    FAB_4:  (_spec_fable_stained_aurora, _paint_fable_stained_aurora),
    FAB_1:  (_spec_fable_ember_glass, _paint_fable_ember_glass),
    FAB_3:  (_spec_fable_abyss_lantern, _paint_fable_abyss_lantern),
    FAB_5:  (_spec_fable_prism_veil, _paint_fable_prism_veil),
    FAB_6:  (_spec_fable_oilforge, _paint_fable_oilforge),
    FAB_7:  (_spec_fable_tempered_dawn, _paint_fable_tempered_dawn),
    FAB_8:  (_spec_fable_pulse_alloy, _paint_fable_pulse_alloy),
    FAB_11:  (_spec_fable_sovereign_flip, _paint_fable_sovereign_flip),
    FAB_12:  (_spec_fable_static_bloom, _paint_fable_static_bloom),
    FAB_13:  (_spec_fable_aurora_travel, _paint_fable_aurora_travel),
    FAB_19:  (_spec_fable_magnetite_flow, _paint_fable_magnetite_flow),
    FAB_15:  (_spec_fable_quicksilver_garden, _paint_fable_quicksilver_garden),
    FAB_16:  (_spec_fable_emberline_drift, _paint_fable_emberline_drift),
})
# === FABLE CRUSH-REBUILD 2026-06-09 (round 2) END ===


# === FABLE CRUSH-REBUILD stragglers via recipe_kit (2026-06-10) ===
from engine.recipe_kit import (micro_scatter as _rk_scatter, filament_web as _rk_web, ring_swarm as _rk_rings,
                               flow_grain as _rk_grain, ramp_lut as _rk_lut,
                               ramp_apply as _rk_ramp, noise01 as _rk_noise)


def _spec_fable_saffron_circuit(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_14, seed)
    web = _rk_web(h, w, s ^ 1, nodes=2600, k=2)
    M = 26 + web * 185 + _rk_scatter(h, w, s ^ 2, 2600, 1.6, "dot") * 55
    R = 205 - _rk_grain(h, w, s ^ 3, 4, 4.5) * 155
    Cc = 24 + _rk_scatter(h, w, s ^ 4, 2200, 2.2, "dot") * 165 + _rk_noise(h, w, s ^ 5, (40, 90)) * 30
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_saffron_circuit(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape); h, w, _ = _work_shape(shape); s = _seed_of(FAB_14, seed)
    web = _rk_web(h, w, s ^ 1, nodes=2600, k=2)
    dens = cv2.GaussianBlur(web, (0, 0), 3)
    lut = _rk_lut([(0.82, 0.55, 0.12), (0.85, 0.30, 0.25), (0.45, 0.13, 0.10)], 0.6)
    eff = _rk_ramp(np.clip(dens * 1.9 + _rk_noise(h, w, s ^ 6, (3, 7)) * 0.28, 0, 1), lut)
    vias = _rk_scatter(h, w, s ^ 2, 2600, 1.6, "dot")
    eff = np.clip(eff * (0.68 + web[..., None] * 0.55) + vias[..., None] * np.float32([0.95, 0.8, 0.4]) * 0.5, 0, 1)
    eff = np.clip(eff * (0.52 + _rk_noise(h, w, s ^ 99, (2, 5))[..., None] * 0.88), 0, 1)
    return _blend_paint(paint, _upscale(eff, fh, fw), _mask2(mask, fh, fw), pm)


def _spec_fable_duomorph(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_17, seed)
    M = 22 + _rk_scatter(h, w, s ^ 1, 5200, 1.6, "star5") * 215
    R = 185 - _rk_grain(h, w, s ^ 2, 3, 4.0) * 130
    Cc = 24 + _rk_scatter(h, w, s ^ 3, 4200, 3.0, "arc") * 175
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_duomorph(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape); h, w, _ = _work_shape(shape); s = _seed_of(FAB_17, seed)
    glyph = _rk_scatter(h, w, s ^ 1, 5200, 1.6, "star5")
    arcs = _rk_scatter(h, w, s ^ 3, 4200, 3.0, "arc")
    spark = _rk_scatter(h, w, s ^ 4, 4200, 1.2, "dot")
    base = _rk_ramp(np.clip(_rk_noise(h, w, s ^ 5, (12, 28)) * 0.7 + 0.1, 0, 1),
                    _rk_lut([(0.13, 0.13, 0.17), (0.22, 0.20, 0.30)], 0.5))
    eff = np.clip(base + glyph[..., None] * np.float32([0.30, 0.26, 0.42]) * 0.55
                  + arcs[..., None] * np.float32([0.16, 0.34, 0.38]) * 0.5
                  + spark[..., None] * np.float32([0.85, 0.72, 0.35]) * 0.30, 0, 1)
    eff = np.clip(eff * (0.52 + _rk_noise(h, w, s ^ 99, (2, 5))[..., None] * 0.88), 0, 1)
    return _blend_paint(paint, _upscale(eff, fh, fw), _mask2(mask, fh, fw), pm)


def _spec_fable_nightbloom(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_18, seed)
    petals = _rk_scatter(h, w, s ^ 1, 7000, 1.5, "petal")
    M = 16 + _rk_scatter(h, w, s ^ 2, 3000, 1.3, "dot") * 205
    R = 195 - _rk_grain(h, w, s ^ 3, 3, 5.0) * 140
    Cc = 26 + cv2.GaussianBlur(petals, (0, 0), 2) * 165 + petals * 45
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_nightbloom(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape); h, w, _ = _work_shape(shape); s = _seed_of(FAB_18, seed)
    petals = _rk_scatter(h, w, s ^ 1, 7000, 1.5, "petal")
    stems = _rk_web(h, w, s ^ 4, nodes=2200, k=2, intensity=(0.2, 0.5))
    base = _rk_ramp(np.clip(_rk_noise(h, w, s ^ 5, (6, 14)), 0, 1),
                    _rk_lut([(0.10, 0.08, 0.22), (0.24, 0.10, 0.30)], 0.55))
    eff = np.clip(base + petals[..., None] * np.float32([0.55, 0.30, 0.62]) * 0.5
                  + stems[..., None] * np.float32([0.18, 0.30, 0.30]) * 0.35, 0, 1)
    eff = np.clip(eff * (0.52 + _rk_noise(h, w, s ^ 99, (2, 5))[..., None] * 0.88), 0, 1)
    return _blend_paint(paint, _upscale(eff, fh, fw), _mask2(mask, fh, fw), pm)


def _spec_fable_comet_parade(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_20, seed)
    M = 20 + _rk_scatter(h, w, s ^ 1, 4200, 1.2, "streak", len_px=4) * 225
    R = np.clip(170 - _rk_scatter(h, w, s ^ 2, 2400, 1.0, "streak", len_px=10) * 125
                + (_rk_noise(h, w, s ^ 3, (4, 9)) - 0.5) * 50, 15, 255)
    Cc = 26 + _rk_scatter(h, w, s ^ 4, 3000, 2.6, "arc") * 180
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_comet_parade(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape); h, w, _ = _work_shape(shape); s = _seed_of(FAB_20, seed)
    heads = _rk_scatter(h, w, s ^ 1, 4200, 1.2, "streak", len_px=4)
    wakes = _rk_scatter(h, w, s ^ 2, 2400, 1.0, "streak", len_px=10)
    base = _rk_ramp(np.clip(_rk_noise(h, w, s ^ 5, (12, 30)), 0, 1),
                    _rk_lut([(0.12, 0.07, 0.26), (0.06, 0.22, 0.30)], 0.55))
    eff = np.clip(base + heads[..., None] * np.float32([0.92, 0.88, 0.75]) * 0.6
                  + wakes[..., None] * np.float32([0.25, 0.55, 0.62]) * 0.4, 0, 1)
    eff = np.clip(eff * (0.52 + _rk_noise(h, w, s ^ 99, (2, 5))[..., None] * 0.88), 0, 1)
    return _blend_paint(paint, _upscale(eff, fh, fw), _mask2(mask, fh, fw), pm)


FABLE_MONOLITHICS.update({
    FAB_14: (_spec_fable_saffron_circuit, _paint_fable_saffron_circuit),
    FAB_17: (_spec_fable_duomorph, _paint_fable_duomorph),
    FAB_18: (_spec_fable_nightbloom, _paint_fable_nightbloom),
    FAB_20: (_spec_fable_comet_parade, _paint_fable_comet_parade),
})
# === FABLE CRUSH-REBUILD stragglers END ===


# === FABLE round-3: SPEC COLOR-DIVERSITY rebuilds (2026-06-10) ===
# Owner doctrine: all three channels swing HARD (~30<->230) at fine scale,
# each on its OWN identity geometry -> multi-hue layered spec composite
# (the broadcast-WTF standard). Paints untouched except nightbloom (+pattern)
# and prism_veil (3x finer threads).

def _spec_fable_abyss_lantern(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_3, seed)
    cores = _rk_scatter(h, w, s ^ 1, 5200, 1.2, "dot")
    plank = _rk_scatter(h, w, s ^ 2, 9000, 0.8, "dot")
    cur = _rk_scatter(h, w, s ^ 3, 5200, 0.9, "streak", len_px=7)
    webs = _rk_web(h, w, s ^ 4, 3600, k=2)
    M = 25 + cores * 215 + plank * 120
    R = np.clip(225 - cur * 190 - _rk_noise(h, w, s ^ 5, (3, 7)) * 40, 15, 255)
    Cc = 28 + webs * 200 + cv2.GaussianBlur(cores, (0, 0), 1.6) * 90
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _spec_fable_comet_parade(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_20, seed)
    heads = _rk_scatter(h, w, s ^ 1, 5200, 1.2, "streak", len_px=4)
    wakes = _rk_scatter(h, w, s ^ 2, 4200, 1.0, "streak", len_px=11)
    bows = _rk_scatter(h, w, s ^ 4, 4200, 2.6, "arc")
    M = 25 + heads * 220
    R = np.clip(35 + wakes * 195, 15, 255)
    Cc = 30 + bows * 205
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _spec_fable_duomorph(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_17, seed)
    glyph = _rk_scatter(h, w, s ^ 1, 5200, 1.6, "star5")
    arcs = _rk_scatter(h, w, s ^ 3, 4200, 3.0, "arc")
    orbits = _rk_scatter(h, w, s ^ 6, 4200, 2.2, "dot")
    M = 28 + glyph * 215
    R = np.clip(225 - arcs * 195, 15, 255)
    Cc = 28 + orbits * 205
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _spec_fable_magnetite_flow(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_19, seed)
    tips = _rk_scatter(h, w, s ^ 1, 7000, 0.9, "dot")
    bands = _rk_grain(h, w, s ^ 2, 2, 3.0)
    pools = _rk_scatter(h, w, s ^ 3, 4200, 2.4, "petal")
    M = 22 + tips * 225
    R = np.clip(40 + bands * 185, 15, 255)
    Cc = 26 + pools * 205
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _spec_fable_nightbloom(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_18, seed)
    pollen = _rk_scatter(h, w, s ^ 2, 6000, 1.0, "star5")
    petals = _rk_scatter(h, w, s ^ 1, 6000, 1.8, "petal")
    stems = _rk_web(h, w, s ^ 4, 3600, k=2)
    M = 24 + pollen * 220 + stems * 90
    R = np.clip(225 - petals * 195, 15, 255)
    Cc = 28 + cv2.GaussianBlur(petals, (0, 0), 1.6) * 130 + stems * 130
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_nightbloom(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape); h, w, _ = _work_shape(shape); s = _seed_of(FAB_18, seed)
    petals = _rk_scatter(h, w, s ^ 1, 6000, 1.8, "petal")
    stems = _rk_web(h, w, s ^ 4, 3600, k=2, intensity=(0.3, 0.7))
    pollen = _rk_scatter(h, w, s ^ 2, 6000, 1.0, "star5")
    base = _rk_ramp(np.clip(_rk_noise(h, w, s ^ 5, (6, 14)), 0, 1),
                    _rk_lut([(0.09, 0.07, 0.20), (0.22, 0.09, 0.28)], 0.55))
    eff = np.clip(base + petals[..., None] * np.float32([0.60, 0.25, 0.65]) * 0.65
                  + stems[..., None] * np.float32([0.20, 0.38, 0.34]) * 0.5
                  + pollen[..., None] * np.float32([0.95, 0.85, 0.55]) * 0.45, 0, 1)
    eff = np.clip(eff * (0.62 + _rk_noise(h, w, s ^ 99, (2, 5))[..., None] * 0.7), 0, 1)
    return _blend_paint(paint, _upscale(eff, fh, fw), _mask2(mask, fh, fw), pm)


def _spec_fable_oilforge(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_6, seed)
    crests = _rk_scatter(h, w, s ^ 1, 6000, 2.0, "arc")
    brush = _rk_grain(h, w, s ^ 2, 4, 2.8)
    glow = _rk_scatter(h, w, s ^ 3, 5200, 1.4, "dot")
    M = 26 + crests * 215
    R = np.clip(40 + brush * 185, 15, 255)
    Cc = 28 + glow * 130 + cv2.GaussianBlur(glow, (0, 0), 1.8) * 95
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _spec_fable_pulse_alloy(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_8, seed)
    ringsA = _rk_rings(h, w, s ^ 1, 4200, 2.4, 1.5)
    grain = _rk_noise(h, w, s ^ 2, (2, 5))
    ringsB = _rk_rings(h, w, s ^ 3, 4200, 3.2, 2.0)
    M = 25 + ringsA * 220
    R = np.clip(230 - grain * 200, 15, 255)
    Cc = 28 + ringsB * 210
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _spec_fable_quicksilver_garden(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_15, seed)
    from engine.recipe_kit import micro_voronoi as _rk_vor
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1600, (h * w) // 26))
    rng = np.random.default_rng(s ^ 2)
    rlut = (rng.random(int(lab.max()) + 1) > 0.5).astype(np.float32)
    clut = (np.random.default_rng(s ^ 3).random(int(lab.max()) + 1) > 0.5).astype(np.float32)
    M = 26 + edge * 215
    R = np.clip(45 + rlut[lab] * 175, 15, 255)
    Cc = 30 + clut[lab] * 185 + np.clip(d1 / max(d1.max(), 1e-5), 0, 1) * 20
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _spec_fable_saffron_circuit(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_14, seed)
    web = _rk_web(h, w, s ^ 1, nodes=2600, k=2)
    etch = _rk_grain(h, w, s ^ 3, 4, 3.5)
    vias = _rk_scatter(h, w, s ^ 4, 5200, 1.4, "dot")
    web2 = _rk_web(h, w, s ^ 6, nodes=2200, k=2)
    M = 26 + web * 215
    R = np.clip(40 + etch * 190, 15, 255)
    Cc = 28 + vias * 150 + web2 * 130
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _spec_fable_stained_aurora(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_4, seed)
    from engine.recipe_kit import micro_voronoi as _rk_vor
    lab, d1, edge = _rk_vor(h, w, s ^ 1, max(1600, (h * w) // 28))
    r1 = np.random.default_rng(s ^ 2).random(int(lab.max()) + 1)
    r2 = np.random.default_rng(s ^ 3).random(int(lab.max()) + 1)
    r3 = np.random.default_rng(s ^ 4).random(int(lab.max()) + 1)
    M = 26 + (r1[lab] > 0.55).astype(np.float32) * (1 - edge) * 210 + edge * 60
    R = np.clip(45 + (r2[lab] > 0.5).astype(np.float32) * 175, 15, 255)
    Cc = 30 + (r3[lab] > 0.5).astype(np.float32) * 175 + np.clip(d1 / max(d1.max(), 1e-5), 0, 1) * 25
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _spec_fable_static_bloom(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(FAB_12, seed)
    dots = _rk_scatter(h, w, s ^ 1, 9000, 0.9, "dot")
    fil = _rk_scatter(h, w, s ^ 2, 5200, 0.9, "streak", len_px=6)
    blooms = _rk_scatter(h, w, s ^ 3, 4200, 2.2, "petal")
    M = 24 + dots * 225
    R = np.clip(230 - fil * 200, 15, 255)
    Cc = 28 + blooms * 130 + cv2.GaussianBlur(blooms, (0, 0), 1.6) * 80
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_prism_veil(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape); h, w, _ = _work_shape(shape); s = _seed_of(FAB_5, seed)
    threads = _rk_web(h, w, s ^ 1, 5200, k=2, intensity=(0.3, 0.75))
    th = np.clip(_rk_noise(h, w, s ^ 2, (3, 8)) + threads * 0.4, 0, 1)
    film = interference_palette(th, 3.0, 0.7, base_srgb=np.float32([0.24, 0.09, 0.15]))
    eff = np.clip(film * (0.7 + threads[..., None] * 0.5), 0, 1)
    eff = np.clip(eff * (0.62 + _rk_noise(h, w, s ^ 99, (2, 5))[..., None] * 0.7), 0, 1)
    return _blend_paint(paint, _upscale(eff, fh, fw), _mask2(mask, fh, fw), pm)


FABLE_MONOLITHICS.update({
    FAB_3: (_spec_fable_abyss_lantern, FABLE_MONOLITHICS[FAB_3][1]),
    FAB_20: (_spec_fable_comet_parade, FABLE_MONOLITHICS[FAB_20][1]),
    FAB_17: (_spec_fable_duomorph, FABLE_MONOLITHICS[FAB_17][1]),
    FAB_19: (_spec_fable_magnetite_flow, FABLE_MONOLITHICS[FAB_19][1]),
    FAB_18: (_spec_fable_nightbloom, _paint_fable_nightbloom),
    FAB_6: (_spec_fable_oilforge, FABLE_MONOLITHICS[FAB_6][1]),
    FAB_8: (_spec_fable_pulse_alloy, FABLE_MONOLITHICS[FAB_8][1]),
    FAB_15: (_spec_fable_quicksilver_garden, FABLE_MONOLITHICS[FAB_15][1]),
    FAB_14: (_spec_fable_saffron_circuit, FABLE_MONOLITHICS[FAB_14][1]),
    FAB_4: (_spec_fable_stained_aurora, FABLE_MONOLITHICS[FAB_4][1]),
    FAB_12: (_spec_fable_static_bloom, FABLE_MONOLITHICS[FAB_12][1]),
    FAB_5: (FABLE_MONOLITHICS[FAB_5][0], _paint_fable_prism_veil),
})
# === FABLE round-3 spec diversity END ===


# === FABLE round-3b: DENSE per-channel fields (2026-06-10) ===
# Round-3a lesson: sparse motifs on dark floors = one giant dark hue class.
# Each channel now rides a SPACE-FILLING hard-swing field (own seed/geometry)
# with the identity motifs spiking on top -> 6-8 hue classes tiled at micro
# scale, decorrelated by construction.

def _f3_chan(motif, filler, lo=38.0, hi=200.0, spike=232.0):
    f = np.maximum(motif, filler * 0.8)
    return lo + f * (hi - lo) / 0.8 * 0.8 + motif * (spike - hi)


def _f3_spec(fid_const, mfn):
    def spec_fn(shape, mask, seed, sm, _m=mfn, _f=fid_const):
        h, w, _ = _work_shape(shape); fh, fw = _shape2(shape); s = _seed_of(_f, seed)
        M, R, Cc = _m(h, w, s)
        M, R, Cc = (_upscale(np.clip(a, 0, 255).astype(np.float32), fh, fw) for a in (M, R, Cc))
        return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)
    return spec_fn


def _f3_abyss(h, w, s):
    cores = _rk_scatter(h, w, s ^ 1, 5200, 1.2, "dot")
    latM = flip_lattice((h, w), s ^ 11, 1.2, 0.5)
    cur = (_rk_grain(h, w, s ^ 3, 2, 3.2) > 0.52).astype(np.float32)
    webs = _rk_web(h, w, s ^ 4, 3600, k=2)
    latC = flip_lattice((h, w), s ^ 12, 2.2, 0.45)
    return (_f3_chan(cores, latM), _f3_chan(cur, flip_lattice((h, w), s ^ 14, 1.6, 0.5), 30, 210),
            _f3_chan(np.clip(webs * 1.2, 0, 1), latC))


def _f3_comet(h, w, s):
    heads = _rk_scatter(h, w, s ^ 1, 5200, 1.2, "streak", len_px=4)
    latM = flip_lattice((h, w), s ^ 11, 1.0, 0.48)
    wakes = _rk_scatter(h, w, s ^ 2, 4200, 1.0, "streak", len_px=11)
    latR = flip_lattice((h, w), s ^ 12, 1.8, 0.52)
    bows = _rk_scatter(h, w, s ^ 4, 4200, 2.6, "arc")
    latC = flip_lattice((h, w), s ^ 13, 2.6, 0.5)
    return (_f3_chan(heads, latM), _f3_chan(wakes, latR, 32, 205), _f3_chan(bows, latC))


def _f3_duomorph(h, w, s):
    glyph = _rk_scatter(h, w, s ^ 1, 5200, 1.6, "star5")
    latM = flip_lattice((h, w), s ^ 11, 1.4, 0.5)
    arcs = _rk_scatter(h, w, s ^ 3, 4200, 3.0, "arc")
    grain = (_rk_grain(h, w, s ^ 12, 3, 2.8) > 0.5).astype(np.float32)
    orbits = _rk_scatter(h, w, s ^ 6, 4200, 2.2, "dot")
    latC = flip_lattice((h, w), s ^ 13, 2.0, 0.46)
    return (_f3_chan(glyph, latM), _f3_chan(arcs, grain, 34, 205), _f3_chan(orbits, latC))


def _f3_magnetite(h, w, s):
    tips = _rk_scatter(h, w, s ^ 1, 7000, 0.9, "dot")
    latM = flip_lattice((h, w), s ^ 11, 1.1, 0.46)
    bands = (_rk_grain(h, w, s ^ 2, 2, 3.0) > 0.5).astype(np.float32)
    pools = _rk_scatter(h, w, s ^ 3, 4200, 2.4, "petal")
    latC = flip_lattice((h, w), s ^ 13, 2.4, 0.5)
    return (_f3_chan(tips, latM), _f3_chan(bands, flip_lattice((h, w), s ^ 14, 1.5, 0.5), 30, 208), _f3_chan(pools, latC))


def _f3_nightbloom(h, w, s):
    pollen = _rk_scatter(h, w, s ^ 2, 6000, 1.0, "star5")
    latM = flip_lattice((h, w), s ^ 11, 1.3, 0.5)
    petals = _rk_scatter(h, w, s ^ 1, 6000, 1.8, "petal")
    latR = flip_lattice((h, w), s ^ 12, 1.7, 0.5)
    stems = _rk_web(h, w, s ^ 4, 3600, k=2)
    latC = flip_lattice((h, w), s ^ 13, 2.3, 0.47)
    return (_f3_chan(pollen, latM), _f3_chan(petals, latR, 33, 206),
            _f3_chan(np.clip(stems * 1.2, 0, 1), latC))


def _f3_oilforge(h, w, s):
    crests = _rk_scatter(h, w, s ^ 1, 6000, 2.0, "arc")
    latM = flip_lattice((h, w), s ^ 11, 1.2, 0.5)
    brush = (_rk_grain(h, w, s ^ 2, 4, 2.8) > 0.52).astype(np.float32)
    glow = _rk_scatter(h, w, s ^ 3, 5200, 1.4, "dot")
    latC = flip_lattice((h, w), s ^ 13, 2.0, 0.5)
    return (_f3_chan(crests, latM), _f3_chan(brush, flip_lattice((h, w), s ^ 14, 1.4, 0.5), 31, 207), _f3_chan(glow, latC))


def _f3_pulse(h, w, s):
    ringsA = _rk_rings(h, w, s ^ 1, 4200, 2.4, 1.5)
    latM = flip_lattice((h, w), s ^ 11, 1.5, 0.5)
    grain = (_rk_noise(h, w, s ^ 2, (2, 5)) > 0.5).astype(np.float32)
    ringsB = _rk_rings(h, w, s ^ 3, 4200, 3.2, 2.0)
    latC = flip_lattice((h, w), s ^ 13, 2.1, 0.48)
    return (_f3_chan(ringsA, latM), _f3_chan(grain, flip_lattice((h, w), s ^ 14, 1.5, 0.5), 32, 206), _f3_chan(ringsB, latC))


def _f3_saffron(h, w, s):
    web = _rk_web(h, w, s ^ 1, nodes=2600, k=2)
    latM = flip_lattice((h, w), s ^ 11, 1.2, 0.5)
    etch = (_rk_grain(h, w, s ^ 3, 4, 3.5) > 0.5).astype(np.float32)
    vias = _rk_scatter(h, w, s ^ 4, 5200, 1.4, "dot")
    web2 = _rk_web(h, w, s ^ 6, nodes=2200, k=2)
    return (_f3_chan(np.clip(web * 1.2, 0, 1), latM), _f3_chan(etch, flip_lattice((h, w), s ^ 14, 1.5, 0.5), 33, 206),
            _f3_chan(np.clip(np.maximum(vias, web2) * 1.1, 0, 1), flip_lattice((h, w), s ^ 13, 2.4, 0.5)))


def _f3_static(h, w, s):
    dots = _rk_scatter(h, w, s ^ 1, 9000, 0.9, "dot")
    latM = flip_lattice((h, w), s ^ 11, 0.9, 0.5)
    fil = _rk_scatter(h, w, s ^ 2, 5200, 0.9, "streak", len_px=6)
    latR = flip_lattice((h, w), s ^ 12, 1.6, 0.5)
    blooms = _rk_scatter(h, w, s ^ 3, 4200, 2.2, "petal")
    latC = flip_lattice((h, w), s ^ 13, 2.8, 0.5)
    return (_f3_chan(dots, latM), _f3_chan(fil, latR, 33, 207), _f3_chan(blooms, latC))


FABLE_MONOLITHICS.update({
    FAB_3: (_f3_spec(FAB_3, _f3_abyss), FABLE_MONOLITHICS[FAB_3][1]),
    FAB_20: (_f3_spec(FAB_20, _f3_comet), FABLE_MONOLITHICS[FAB_20][1]),
    FAB_17: (_f3_spec(FAB_17, _f3_duomorph), FABLE_MONOLITHICS[FAB_17][1]),
    FAB_19: (_f3_spec(FAB_19, _f3_magnetite), FABLE_MONOLITHICS[FAB_19][1]),
    FAB_18: (_f3_spec(FAB_18, _f3_nightbloom), FABLE_MONOLITHICS[FAB_18][1]),
    FAB_6: (_f3_spec(FAB_6, _f3_oilforge), FABLE_MONOLITHICS[FAB_6][1]),
    FAB_8: (_f3_spec(FAB_8, _f3_pulse), FABLE_MONOLITHICS[FAB_8][1]),
    FAB_14: (_f3_spec(FAB_14, _f3_saffron), FABLE_MONOLITHICS[FAB_14][1]),
    FAB_12: (_f3_spec(FAB_12, _f3_static), FABLE_MONOLITHICS[FAB_12][1]),
})
# === FABLE round-3b END ===


# === IGNITION REBUILD 2026-06-10 START ===
# --- IGNITION: fable_comet_parade ---
# ============================================================================
# ===== FABLE: COMET PARADE -- IGNITION REBUILD (2026-06-10, round 4) ========
# Owner round-3 verdict: 'Spec not working with paint.'  Fix = the Wovenlight
# principle: ONE rng stream lays out every comet (center, heading, caste) and
# BOTH paint and spec read the SAME splat arrays.  Two castes, one parade:
#   GILDED comets -- amber-to-gold heads/tails painted bright; R rides their
#       soft wake corridors (visible as faint teal mist in the albedo).
#   GHOST comets -- barely-there violet-dark capsules in the paint that carry
#       M ~ 240 on those exact pixels: a hidden mirror parade, invisible at
#       most angles, that DETONATES when the sun lines up.
# Every comet (both castes) tows a bow-shock crescent at its own head on its
# own heading; Cc rides those arcs (the thin teal crescents in the paint).
# Scattered multi-angle headings = UV-orientation-agnostic by construction;
# the nebula floor stays calm so the parade reads against quiet.
# ============================================================================


@_memo_fields
def _comet_parade_ign_fields(h, w, seed):
    '''Shared comet-parade geometry (the marriage contract): paint and spec
    both read these arrays, built from one seeded rng stream.
    Returns (gild, ghost, wakecorr, bow, nebula, grain).'''
    m = float(max(h, w))
    px = m / 1024.0
    ar = (h * w) / (1024.0 * 1024.0)
    yy, xx, _, _ = _coords(h, w)
    rng = np.random.default_rng((seed ^ 0x4A11AD) & 0x7FFFFFFF)
    gild = np.zeros((h, w), np.float32)
    ghost = np.zeros((h, w), np.float32)
    wakecorr = np.zeros((h, w), np.float32)
    bow = np.zeros((h, w), np.float32)
    n = max(90, int(round(1300 * ar)))
    for _ in range(n):
        cy = float(rng.uniform(0.0, h))
        cx = float(rng.uniform(0.0, w))
        ang = float(rng.uniform(0.0, 2.0 * np.pi))
        is_ghost = rng.random() < 0.55
        ca = float(np.cos(ang))
        sa = float(np.sin(ang))
        if is_ghost:
            # GHOST capsule: flat-core mirror streak + bulbed head (M's pixels)
            L = float(rng.uniform(18.0, 40.0)) * px
            wv = max(float(rng.uniform(1.9, 3.0)) * px, 1.2)
            amp = float(rng.uniform(0.93, 1.0))
            y0, y1, x0, x1 = _opt_rect_win(h, w, cy, cx, ca, sa,
                                           -8.0 * px, L + 3.0 * px,
                                           max(wv + 2.0 * px, 7.5 * px))
            dy = yy[y0:y1, x0:x1] - cy
            dx = xx[y0:y1, x0:x1] - cx
            u = dx * ca + dy * sa
            v = dy * ca - dx * sa
            edge = max(0.9 * px, 0.7)
            cross = np.clip((wv - np.abs(v)) / edge, 0.0, 1.0)
            along = (np.clip((u + 2.0 * px) / max(1.6 * px, 1.0), 0.0, 1.0)
                     * np.clip((L - u) / max(2.8 * px, 1.0), 0.0, 1.0))
            head = np.exp(-(u * u + v * v) / (2.0 * max(2.4 * px, 1.2) ** 2))
            sub = ghost[y0:y1, x0:x1]
            np.maximum(sub, np.maximum(cross * along, head) * amp, out=sub)
            bow_amp = 0.50
            r0 = float(rng.uniform(4.5, 8.0)) * px
        else:
            # GILDED comet: bright head + decaying tail (paint's gold) and a
            # wider soft wake corridor on the SAME center/heading (R's pixels)
            tl = float(rng.uniform(14.0, 30.0)) * px
            sv = max(float(rng.uniform(1.5, 2.4)) * px, 1.0)
            amp = float(rng.uniform(0.60, 1.0))
            cs = 2.6 * sv
            y0, y1, x0, x1 = _opt_rect_win(h, w, cy, cx, ca, sa,
                                           -8.0 * px, 4.2 * tl, 3.2 * cs)
            dy = yy[y0:y1, x0:x1] - cy
            dx = xx[y0:y1, x0:x1] - cx
            u = dx * ca + dy * sa
            v = dy * ca - dx * sa
            head = np.exp(-(u * u + v * v) / (2.0 * max(2.1 * px, 1.1) ** 2))
            tail = (np.exp(-np.maximum(u, 0.0) / tl)
                    * np.exp(-(v * v) / (2.0 * sv * sv)) * (u > -2.0 * px))
            sub = gild[y0:y1, x0:x1]
            np.maximum(sub, np.maximum(head, tail * 0.85) * amp, out=sub)
            corr = (np.exp(-np.maximum(u, 0.0) / (1.7 * tl))
                    * np.exp(-(v * v) / (2.0 * cs * cs)) * (u > -4.0 * px))
            sub2 = wakecorr[y0:y1, x0:x1]
            np.maximum(sub2, corr * (0.55 + 0.45 * amp), out=sub2)
            bow_amp = 0.95 * amp
            r0 = float(rng.uniform(5.0, 10.0)) * px
        # bow shock: a crescent towed in FRONT of THIS head, on THIS heading
        lw = max(float(rng.uniform(1.6, 2.6)) * px, 0.9)
        spread = float(rng.uniform(0.55, 0.95))
        by0, by1, bx0, bx1 = _opt_win(h, w, cy, cx, r0 + 4.0 * lw)
        bdy = yy[by0:by1, bx0:bx1] - cy
        bdx = xx[by0:by1, bx0:bx1] - cx
        rr = np.sqrt(bdy * bdy + bdx * bdx) + 1e-6
        th = np.arctan2(bdy, bdx)
        dd = np.mod(th - ang + np.pi, 2.0 * np.pi) - np.pi
        crest = np.exp(-((rr - r0) / lw) ** 2) * np.exp(-(dd / spread) ** 2)
        sub3 = bow[by0:by1, bx0:bx1]
        np.maximum(sub3, crest * bow_amp, out=sub3)
    sr = px
    nebula = _msc(h, w, [max(11, int(26 * sr)), max(25, int(62 * sr)),
                         max(53, int(140 * sr))], seed ^ 0x3B7A19)
    grain = _msc(h, w, [2, 5], seed ^ 0x5D2C0B)
    return (np.clip(gild, 0.0, 1.0).astype(np.float32),
            np.clip(ghost, 0.0, 1.0).astype(np.float32),
            np.clip(wakecorr, 0.0, 1.0).astype(np.float32),
            np.clip(bow, 0.0, 1.0).astype(np.float32),
            nebula.astype(np.float32), grain.astype(np.float32))


def _spec_fable_comet_parade(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of('fable_comet_parade', seed)
    gild, ghost, wakecorr, bow, nebula, grain = _comet_parade_ign_fields(h, w, s)
    rgrain = _msc(h, w, [3, 8], s ^ 0x6E1F2A)
    # M -- IGNITION: the ghost parade. Near-invisible violet-dark capsules in
    # the paint carry mirror-max M on the SAME pixels; gilded comets only get
    # a satin gleam; calm low floor everywhere else.
    M = 24.0 + 232.0 * np.clip(ghost * 1.6, 0.0, 1.0) + 34.0 * gild + 12.0 * (grain - 0.5)
    # R -- a different ASPECT of the same parade: the gilded wake corridors
    # (the faint teal mist the paint shows) run rough-velvet; ghost mirror
    # capsules are POLISHED, so R dives on exactly those streaks.
    R = 82.0 + 126.0 * wakecorr - 36.0 * ghost + 22.0 * (rgrain - 0.5)
    # Cc -- third aspect: bow-shock crescents towed by every comet head (the
    # thin teal arcs in the paint) over a slow nebula breath.
    Cc = 44.0 + 198.0 * bow + 26.0 * (nebula - 0.5)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_comet_parade(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of('fable_comet_parade', seed)
    gild, ghost, wakecorr, bow, nebula, grain = _comet_parade_ign_fields(h, w, s)
    # calm deep indigo-to-violet nebula floor (OKLab ramp keeps it rich)
    base = _opt_oklch_ramp([(0.020, 0.022, 0.078), (0.066, 0.056, 0.188),
                            (0.158, 0.108, 0.318)], nebula, flatten_lightness=0.30)
    # faint teal wake mist -- the exact corridors R roughens
    eff = base + wakecorr[..., None] * np.float32([0.05, 0.15, 0.19]) * 0.32
    # gilded comets: amber tails running to white-gold heads (crisp blend)
    goldt = np.clip(gild * 1.12, 0.0, 1.0)
    gold = _opt_oklch_ramp([(0.140, 0.058, 0.012), (0.700, 0.408, 0.092),
                            (1.000, 0.892, 0.580)], goldt, flatten_lightness=0.10)
    a = (goldt ** 1.25)[..., None]
    eff = eff * (1.0 - a) + gold * a
    # GHOST parade: quiet violet-dark capsules on the very pixels where M
    # detonates -- nearly invisible here, explosive in the spec
    g = ghost[..., None]
    eff = eff * (1.0 - 0.45 * g) + g * np.float32([0.075, 0.028, 0.150]) * 0.42
    # bow-shock crescents: thin teal arcs towed ahead of every head
    eff = eff + bow[..., None] * np.float32([0.10, 0.50, 0.56]) * 0.48
    # stardust breath
    eff = eff + ((grain - 0.5) * 0.030)[..., None]
    eff = np.clip(eff, 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


FABLE_MONOLITHICS.update({
    FAB_20: (_spec_fable_comet_parade, _paint_fable_comet_parade),
})


# --- IGNITION: fable_magnetite_flow ---
# ============================================================================
# FABLE #19 - MAGNETITE FLOW (fable_magnetite_flow) - IGNITION REBUILD (r4)
# Owner round-3 verdict: "Spec not married to paint."  Cure = the Wovenlight
# principle: ONE shared dipole-field generator feeds BOTH paint and spec with
# the SAME seed, so every spec feature sits on geometry you can SEE.
# Look: iron-filing filaments combed along the equipotential contours of 18
# scattered magnetic poles (the filings wrap and densify around each pole --
# scattered + radial + meandering, UV-orientation-agnostic).  The poles split
# the car into NORTH and SOUTH polarity territories separated by thin dark
# domain walls.
#   SOUTH = the visible body read: fine bright blued-steel filings combed
#           over a deep blue-black ground; the spec stays satin-calm there.
#   NORTH = the IGNITION: the very same filament crests render near-black
#           magnetite in the paint (a charcoal-violet whisper) but carry
#           M ~ 250 on those exact pixels -- invisible at most angles, then
#           half the car's filings DETONATE as molten mirror threads when
#           the sun lines up.
# Channel aspects of the ONE motif system (never alien geometry):
#   M  = north-territory filament crests (the hidden mirror threads)
#   R  = domain-wall corridors + anti-phase filament flanks
#   Cc = pole-core gloss wells + drifting macro sheen
# ============================================================================

_magnetite_flow_ign_cache = {}


def _magnetite_flow_ign_fields(h, w, seed):
    """Shared dipole geometry -> (crest, flank, relief, north, wall,
    corridor, pools, macro); paint and spec both eat THIS tuple."""
    key = (int(h), int(w), int(seed))
    hit = _magnetite_flow_ign_cache.get(key)
    if hit is not None:
        return hit
    m = float(max(h, w))
    px = m / 1024.0
    yy, xx, _, _ = _coords(h, w)
    rng = np.random.default_rng((seed ^ 0x3A6E19) & 0x7FFFFFFF)
    nd = 26
    cy = rng.uniform(0.04 * h, 0.96 * h, nd).astype(np.float32)
    cx = rng.uniform(0.04 * w, 0.96 * w, nd).astype(np.float32)
    sgn = np.ones(nd, np.float32)
    sgn[: nd // 2] = -1.0
    sgn = sgn[rng.permutation(nd)]            # balanced N/S poles, both present
    q = sgn * rng.uniform(0.75, 1.25, nd).astype(np.float32)
    sig = (rng.uniform(22.0, 44.0, nd) * px).astype(np.float32)
    rmin2 = np.float32(max(14.0 * px, 8.0) ** 2)
    # nearest/second-nearest pole ownership (cKDTree-backed, render-time safe)
    d1, d2, own = _opt_voro_top2(yy, xx, cy, cx, k=4)
    north = (q[own] > 0.0).astype(np.float32)
    gsep = (np.sqrt(d2) - np.sqrt(d1)).astype(np.float32)
    wall = np.exp(-((gsep / max(3.0 * px, 2.0)) ** 2)).astype(np.float32)
    corridor = np.exp(-((gsep / max(10.0 * px, 7.0)) ** 2)).astype(np.float32)
    pools = np.exp(-d1 / (sig[own] * sig[own])).astype(np.float32)
    # scalar magnetic potential (in-place accumulation, no per-pixel python)
    phi = np.zeros((h, w), np.float32)
    for i in range(nd):
        dy = yy - cy[i]
        dx = xx - cx[i]
        np.multiply(dy, dy, out=dy)
        np.multiply(dx, dx, out=dx)
        dy += dx
        dy += rmin2
        np.log(dy, out=dy)
        np.multiply(dy, q[i], out=dy)
        phi += dy
    # filament phase: equipotential contours of the pole field, noise-warped
    # so the filings meander (no straight stripes anywhere on the UV)
    warp = (_msc(h, w, [max(7, int(15 * px)), max(15, int(40 * px))], seed ^ 0x3B7F2A) - 0.5) * 2.0
    ph = np.float32(6.2) * phi + warp * np.float32(1.3)
    cosf = np.cos(2.0 * np.pi * ph).astype(np.float32)
    crest = ((0.5 - 0.5 * cosf) ** 3).astype(np.float32)    # sharp filing crests
    flank = ((0.5 + 0.5 * cosf) ** 3).astype(np.float32)    # anti-phase flanks
    relief = (0.5 - 0.5 * cosf).astype(np.float32)          # soft full profile
    macro = _msc(h, w, [max(19, int(63 * px)), max(45, int(160 * px))], seed ^ 0x3D9C4B).astype(np.float32)
    out = (crest, flank, relief, north, wall, corridor, pools, macro)
    if len(_magnetite_flow_ign_cache) > 4:
        _magnetite_flow_ign_cache.clear()
    _magnetite_flow_ign_cache[key] = out
    return out


def _spec_fable_magnetite_flow(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of("fable_magnetite_flow", seed)
    crest, flank, relief, north, wall, corridor, pools, macro = _magnetite_flow_ign_fields(h, w, s)
    g1 = np.random.default_rng((s ^ 0x19C4F2) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    # M -- IGNITION: the north-territory filament crests detonate as mirror
    # threads on the EXACT pixels the paint renders near-black; the south
    # filings keep only a satin whisper; domain walls kill the flare.
    M = (24.0 + 244.0 * north * crest + 12.0 * (1.0 - north) * crest) * (1.0 - 0.55 * wall)
    # R -- its own ASPECT of the same system: wide domain-wall corridors plus
    # the anti-phase filament flanks (the wet valleys between the filings).
    R = 72.0 + 122.0 * corridor + 46.0 * (flank - 0.5) + 14.0 * (g1 - 0.5)
    # Cc -- third aspect: wet gloss wells around every pole core + macro sheen
    Cc = 54.0 + 168.0 * pools + 40.0 * (macro - 0.5) - 24.0 * wall
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_magnetite_flow(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of("fable_magnetite_flow", seed)
    crest, flank, relief, north, wall, corridor, pools, macro = _magnetite_flow_ign_fields(h, w, s)
    # SOUTH: the visible blued-steel filings -- fine bright filaments riding
    # the SAME relief the spec reads, over a deep blue-black ground
    t_s = np.clip(0.08 + 0.62 * relief + 0.22 * crest + 0.08 * (macro - 0.5), 0.0, 1.0)
    steel = _opt_oklch_ramp([(0.018, 0.026, 0.052), (0.155, 0.205, 0.300), (0.560, 0.620, 0.720)],
                            t_s, flatten_lightness=0.12)
    # NORTH: the hidden mirror territory -- near-black magnetite; the ignition
    # crests get only a charcoal-violet whisper (M does the talking up there)
    t_n = np.clip(0.10 + 0.30 * relief + 0.16 * crest, 0.0, 1.0)
    magnet = _opt_oklch_ramp([(0.014, 0.012, 0.024), (0.052, 0.044, 0.082), (0.115, 0.095, 0.165)],
                             t_n, flatten_lightness=0.18)
    n3 = north[..., None]
    eff = steel * (1.0 - n3) + magnet * n3
    # thin wet near-black domain walls between the polarity territories
    eff = eff * (1.0 - 0.58 * wall)[..., None]
    # the pole-core gloss wells kiss the albedo (Cc owns the real glow)
    eff = np.clip(eff * (0.93 + 0.13 * pools[..., None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


FABLE_MONOLITHICS.update({
    "fable_magnetite_flow": (_spec_fable_magnetite_flow, _paint_fable_magnetite_flow),
})


# --- IGNITION: fable_nightbloom ---
# ============================================================================
# ===== FABLE: NIGHTBLOOM — IGNITION REBUILD (FAB_18, 2026-06-10) ============
# Midnight garden rebuilt on the Wovenlight principle: ONE shared field fn
# feeds paint AND spec (same seed, same pixels), so every spec highlight
# lands on geometry the paint actually draws. Ink-plum petal rosettes at
# random centers/rotations (UV-agnostic) sleep almost invisibly against an
# indigo dusk floor; gold pollen embers glow at their hearts; thin jade
# moon-vine filaments arc off the blooms with faint perfume rings breathing
# around each rosette.
# IGNITION (dark-hidden polarity): the petal fans are painted DEEP
# (deep-lightness plum ramp, barely-there silhouettes) but carry M~250 on
# those exact pixels — at most angles the car reads as a quiet night garden,
# then the sun lines up and the whole field detonates into silver bloom
# fans. CALM: dusk floor, vines and rings hold M at the floor. ASPECTS of
# the one motif system: M = petal combs, R = vine + perfume-ring gloss
# corridors, Cc = pollen-ember glaze + moon-dew sheen pools.
# ============================================================================


@_memo_fields
def _nightbloom_ign_fields(h, w, seed):
    """Shared geometry for paint AND spec — same seed -> same pixels.
    Returns (petal, core, ring, vine, pollen, dusk, dew):
      petal  — angular petal-fan combs of 330 scattered rosettes (IGNITION)
      core   — tight rosette hearts (gold pollen-ember anchors)
      ring   — thin perfume annuli breathing just outside each rosette
      vine   — curved moon-vine filaments arcing off the blooms (cv2 AA)
      pollen — micro pollen dust drifting between blooms
      dusk   — radial-from-scattered-anchors midnight carrier (no up/down)
      dew    — third-angle warped moon-dew sheen pools
    """
    rng = np.random.default_rng((seed ^ 0x3B100D) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    m = float(max(h, w))
    sr = m / 1024.0
    petal = np.zeros((h, w), np.float32)
    core = np.zeros((h, w), np.float32)
    ring = np.zeros((h, w), np.float32)
    vcan = np.zeros((h, w), np.uint8)
    tt = np.linspace(0.0, 1.0, 22, dtype=np.float32)
    for _ in range(650):
        cy = float(rng.uniform(0.0, h))
        cx = float(rng.uniform(0.0, w))
        rot = float(rng.uniform(0.0, 2.0 * np.pi))
        rb = float(rng.uniform(8.0, 18.0)) * sr
        npet = int(rng.integers(5, 9))
        amp = float(rng.uniform(0.70, 1.0))
        ext = rb * 1.62
        y0 = max(int(cy - ext) - 1, 0)
        y1 = min(int(cy + ext) + 2, h)
        x0 = max(int(cx - ext) - 1, 0)
        x1 = min(int(cx + ext) + 2, w)
        dy = yy[y0:y1, x0:x1] - cy
        dx = xx[y0:y1, x0:x1] - cx
        r = np.sqrt(dy * dy + dx * dx) + 1e-6
        th = np.arctan2(dy, dx)
        comb = np.clip(np.cos(npet * (th - rot)), 0.0, 1.0) ** 2
        body = np.clip(1.0 - r / rb, 0.0, 1.0) ** 0.55
        sub = petal[y0:y1, x0:x1]
        np.maximum(sub, comb * body * amp, out=sub)
        subc = core[y0:y1, x0:x1]
        np.maximum(subc, np.exp(-(r / (rb * 0.22)) ** 2) * amp, out=subc)
        subr = ring[y0:y1, x0:x1]
        np.maximum(subr, np.exp(-((r - rb * 1.30) / (rb * 0.085)) ** 2) * amp,
                   out=subr)
        # moon-vine: a curved arc leaving the rosette (any direction — UV-safe)
        if rng.random() < 0.7:
            va = rot + float(rng.uniform(-0.6, 0.6))
            vl = rb * float(rng.uniform(2.0, 3.6))
            bend = rb * float(rng.uniform(-1.1, 1.1))
            ca = float(np.cos(va))
            sa = float(np.sin(va))
            bx = cx + ca * vl * tt - sa * bend * (tt * tt)
            by = cy + sa * vl * tt + ca * bend * (tt * tt)
            pts = np.stack([bx, by], axis=1).astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(vcan, [pts], False, 255,
                          max(1, int(round(sr))), cv2.LINE_AA)
    vine = cv2.GaussianBlur(vcan.astype(np.float32) / 255.0, (0, 0),
                            max(0.6, 0.7 * sr))
    vine = np.clip(vine * 1.5, 0.0, 1.0).astype(np.float32)
    # pollen dust: seeded impulse scatter, softened to 2-4 px motes
    n_dust = 4200
    dyi = rng.uniform(0.0, h - 1.0, n_dust).astype(np.int32)
    dxi = rng.uniform(0.0, w - 1.0, n_dust).astype(np.int32)
    da = rng.uniform(0.5, 1.0, n_dust).astype(np.float32)
    imp = np.zeros((h, w), np.float32)
    np.maximum.at(imp, (dyi, dxi), da)
    soft = cv2.GaussianBlur(imp, (0, 0), max(0.8, 1.0 * sr))
    pollen = np.clip(soft / max(float(soft.max()), 1e-6), 0.0, 1.0).astype(np.float32)
    # midnight dusk carrier: radial from 7 scattered anchors (never top-down)
    dusk = np.zeros((h, w), np.float32)
    for _ in range(12):
        ay = float(rng.uniform(0.0, h))
        ax = float(rng.uniform(0.0, w))
        reach = float(rng.uniform(0.16, 0.32)) * m
        aa = float(rng.uniform(0.6, 1.0))
        r2 = (yy - ay) ** 2 + (xx - ax) ** 2
        dusk += np.exp(-r2 / (2.0 * reach * reach)) * aa
    dusk = (dusk / max(float(dusk.max()), 1e-6)).astype(np.float32)
    # third-angle moon-dew sheen pools (Cc's wandering aspect)
    a3 = float(rng.uniform(0.0, np.pi))
    p3 = max(40.0, float(rng.uniform(150.0, 230.0)) * sr)
    w3 = (_msc(h, w, [max(17, int(67 * sr)), max(43, int(171 * sr))],
               seed ^ 0x5D0E) - 0.5) * (40.0 * sr)
    c3 = (xx * np.cos(a3) + yy * np.sin(a3) + w3) / p3
    dew = ((0.5 + 0.5 * np.sin(2.0 * np.pi * c3)) ** 2.0).astype(np.float32)
    return petal, core, ring, vine, pollen, dusk, dew


def _spec_fable_nightbloom(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of("fable_nightbloom", seed)
    petal, core, ring, vine, pollen, dusk, dew = _nightbloom_ign_fields(h, w, s)
    grain = _msc(h, w, [3, 7, 17], s ^ 0x9E11)
    # M — IGNITION: the ink-dark petal fans detonate near-max on the SAME
    # pixels the paint draws them; pollen dust twinkles silver; the gold
    # ember hearts stay paint-bright (Cc owns them), everything else calm.
    pet_hot = np.clip(petal / 0.26, 0.0, 1.0) ** 0.7
    M = (22.0 + 232.0 * pet_hot + 36.0 * pollen) * (1.0 - 0.45 * core)
    # R — its own aspect: moon-vines + perfume rings are the gloss corridors
    # cut into a soft-grained garden floor; petals run a touch glassier.
    R = (176.0 - 134.0 * np.maximum(vine, ring) - 24.0 * pet_hot
         + 30.0 * (grain - 0.5))
    # Cc — saffron-style echo: the gold pollen embers (hearts + dust) get the
    # wet glaze on their exact paint pixels, pooling with the moon-dew sheen.
    ember = np.maximum(core, pollen * 0.85)
    Cc = (30.0 + 185.0 * ember + 36.0 * dew
          - 14.0 * np.maximum(vine, ring))
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_nightbloom(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of("fable_nightbloom", seed)
    petal, core, ring, vine, pollen, dusk, dew = _nightbloom_ign_fields(h, w, s)
    # indigo dusk floor — radial from scattered anchors, never top-to-bottom
    t_b = np.clip(0.12 + 0.72 * dusk + 0.10 * (dew - 0.5), 0.0, 1.0)
    base = _opt_oklch_ramp([(0.042, 0.036, 0.120), (0.082, 0.058, 0.210),
                            (0.148, 0.088, 0.262)], t_b, flatten_lightness=0.3)
    # IGNITION MOTIF, dark polarity: ink-plum petal fans — quiet silhouettes
    # on a deep-lightness ramp; spec M detonates these exact pixels.
    plum = _opt_oklch_ramp([(0.050, 0.016, 0.082), (0.128, 0.030, 0.148),
                            (0.335, 0.100, 0.360)],
                           np.clip(petal, 0.0, 1.0), flatten_lightness=0.2)
    pw = np.clip(petal / 0.12, 0.0, 1.0)[..., None]
    eff = base * (1.0 - pw) + plum * pw
    # moon-vines: thin muted jade filaments; perfume rings breathe faint violet
    v3 = np.clip(vine / 0.34, 0.0, 1.0)[..., None]
    eff = eff * (1.0 - v3) + np.float32([0.085, 0.185, 0.165]) * v3
    eff = eff + ring[..., None] * np.float32([0.15, 0.09, 0.24]) * 0.26
    # gold pollen embers at the rosette hearts + dust drifting between blooms
    ember = np.maximum(core, pollen * 0.80)
    gold = _opt_oklch_ramp([(0.44, 0.27, 0.075), (1.00, 0.85, 0.44)],
                           np.clip(ember * 1.25, 0.0, 1.0))
    e3 = (np.clip(ember / 0.50, 0.0, 1.0) ** 1.3)[..., None]
    eff = eff * (1.0 - e3) + gold * e3
    # the moon-dew pools kiss the albedo (the clearcoat carries the real sheen)
    eff = np.clip(eff * (0.93 + 0.14 * dew[..., None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


FABLE_MONOLITHICS.update({
    "fable_nightbloom": (_spec_fable_nightbloom, _paint_fable_nightbloom),
})


# --- IGNITION: fable_oilforge ---
# ============================================================================
# ===== FABLE: OILFORGE (fable_oilforge) — IGNITION REBUILD 2026-06-10 =======
# The forge floor: dark multi-angle brushed gunmetal scattered with hundreds
# of micro oil-film rings in TWO castes sharing ONE generator. LIVE rings
# bloom committed copper->gold->teal->indigo film orders in the albedo but
# stay satin in spec. QUENCH pools are the ignition: near-black glass in the
# paint, yet those SAME pixels run a mirror plateau (M~205) with ring crests
# to ~252 — invisible oil-slick black at most angles, then the sun lines up
# and the panel detonates into rings of light, each pool wearing an ember
# corona (Cc annulus OUTSIDE the mirror core, so M and Cc decorrelate). R
# rides a third aspect of the same motif: the brushed forge grain, wet-sanded
# smooth inside every ring footprint. UV-agnostic: scattered epicenters plus
# three random scratch axes; no upright geometry anywhere.
# ============================================================================


@_memo_fields
def _oilforge_ign_fields(h, w, seed):
    '''Shared geometry for fable_oilforge paint + spec (Wovenlight principle).
    Returns (pres_l, frac_l, crest_l, halo_l, pres_q, frac_q, crest_q,
    ember_q, grain, pool, glint) — all float32 HxW on the work grid.'''
    m = float(max(h, w))
    sr = m / 1024.0
    yy, xx, _, _ = _coords(h, w)
    rng = np.random.default_rng((seed ^ 0x0F6E12) & 0x7FFFFFFF)

    def _splat(count, tag, ember):
        rr = np.random.default_rng((seed ^ tag) & 0x7FFFFFFF)
        thick = np.zeros((h, w), np.float32)
        glow = np.zeros((h, w), np.float32)
        for _ in range(count):
            cy = rr.uniform(0.0, h)
            cx = rr.uniform(0.0, w)
            reach = max(2.0, rr.uniform(0.0018, 0.0038) * m)
            amp = rr.uniform(0.62, 1.0)
            rad = (3.4 if ember else 3.0) * reach
            y0 = max(int(cy - rad) - 1, 0)
            y1 = min(int(cy + rad) + 2, h)
            x0 = max(int(cx - rad) - 1, 0)
            x1 = min(int(cx + rad) + 2, w)
            r = np.sqrt((yy[y0:y1, x0:x1] - cy) ** 2 + (xx[y0:y1, x0:x1] - cx) ** 2)
            sub = thick[y0:y1, x0:x1]
            np.maximum(sub, (np.exp(-r / reach) * amp).astype(np.float32), out=sub)
            if ember:
                g = np.exp(-(((r - 2.1 * reach) / (0.75 * reach)) ** 2)) * (amp * 0.85)
            else:
                g = np.exp(-((r / (reach * 1.8)) ** 2)) * (amp * 0.60)
            glow[y0:y1, x0:x1] += g.astype(np.float32)
        return thick, np.clip(glow, 0.0, 1.0).astype(np.float32)

    # LIVE rings (colour film in paint) and QUENCH pools (the hidden mirrors)
    thick_l, halo_l = _splat(max(330, int(round(2000 * sr * sr))), 0x3A91B7, False)
    thick_q, ember_q = _splat(max(400, int(round(2600 * sr * sr))), 0x5C24D9, True)
    pres_l = np.clip((thick_l - 0.10) * 8.0, 0.0, 1.0).astype(np.float32)
    pres_q = np.clip((thick_q - 0.10) * 8.0, 0.0, 1.0).astype(np.float32)
    b_l = thick_l * 6.5
    b_q = thick_q * 6.5
    frac_l = (b_l - np.floor(b_l)).astype(np.float32)
    frac_q = (b_q - np.floor(b_q)).astype(np.float32)
    crest_l = (np.exp(-((frac_l - 0.55) / 0.11) ** 2) * pres_l).astype(np.float32)
    crest_q = (np.exp(-((frac_q - 0.55) / 0.13) ** 2) * pres_q).astype(np.float32)
    # forge brush: 3 random scratch axes (UV-agnostic), domain-warped micro
    grain = np.zeros((h, w), np.float32)
    warp = (_msc(h, w, [max(13, int(47 * sr)), max(31, int(119 * sr))], seed ^ 0x77A3E1) - 0.5) * (7.0 * sr)
    for _k in range(3):
        ang = rng.uniform(0.0, np.pi)
        period = max(2.0, rng.uniform(2.2, 3.4) * sr)
        ph = rng.uniform(0.0, 2.0 * np.pi)
        proj = np.cos(ang) * xx + np.sin(ang) * yy
        srt = 0.5 + 0.5 * np.sin((proj + warp) * (2.0 * np.pi / period) + ph)
        np.maximum(grain, (srt ** 3).astype(np.float32), out=grain)
    grain = (0.74 * grain + 0.26 * _msc(h, w, [2, 5], seed ^ 0x4D8F2B)).astype(np.float32)
    # macro breath for Cc + micro glint for the calm floor
    pool = _msc(h, w, [max(23, int(79 * sr)), max(51, int(180 * sr))], seed ^ 0x66C1A5).astype(np.float32)
    glint = _msc(h, w, [2, 4], seed ^ 0x2B9E63).astype(np.float32)
    return pres_l, frac_l, crest_l, halo_l, pres_q, frac_q, crest_q, ember_q, grain, pool, glint


def _spec_fable_oilforge(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of('fable_oilforge', seed)
    (pres_l, frac_l, crest_l, halo_l, pres_q, frac_q, crest_q,
     ember_q, grain, pool, glint) = _oilforge_ign_fields(h, w, s)
    # M — IGNITION: the quench pools (near-black in paint) run a mirror
    # plateau with their ring crests reaching ~252 on the SAME pixels the
    # paint keeps dark; the rest of the panel holds a calm low floor.
    M = 18.0 + 184.0 * pres_q + 50.0 * crest_q + 12.0 * glint * (1.0 - pres_q)
    # R — its OWN aspect of the motif: brushed forge grain between rings,
    # wet-sanded smooth inside every ring footprint (the oil polishes steel).
    pres_any = np.maximum(pres_l, pres_q)
    R = 150.0 + 92.0 * (grain - 0.5) * (1.0 - 0.75 * pres_any) - 58.0 * pres_any + 10.0 * (glint - 0.5)
    # Cc — third aspect: ember coronas living OUTSIDE each mirror core
    # (annular afterglow) + wet-coat glow on the live colour rings + macro.
    Cc = 26.0 + 136.0 * ember_q + 32.0 * halo_l + 44.0 * pool
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_oilforge(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of('fable_oilforge', seed)
    (pres_l, frac_l, crest_l, halo_l, pres_q, frac_q, crest_q,
     ember_q, grain, pool, glint) = _oilforge_ign_fields(h, w, s)
    # forged gunmetal floor — dark blue-grey steel under multi-angle brush
    t_g = np.clip(0.18 + 0.55 * grain + 0.14 * (pool - 0.5), 0.0, 1.0)
    steel = _opt_oklch_ramp([(0.040, 0.046, 0.056), (0.105, 0.118, 0.135), (0.190, 0.205, 0.228)],
                            t_g, flatten_lightness=0.2)
    # LIVE oil rings — committed copper->gold->teal->indigo film orders
    film = _opt_oklch_ramp([(0.34, 0.13, 0.05), (0.95, 0.62, 0.16),
                            (0.05, 0.42, 0.40), (0.10, 0.08, 0.34)],
                           frac_l, flatten_lightness=0.1)
    film = film * (0.58 + 0.42 * crest_l)[..., None]
    pl = (pres_l * 0.85)[..., None]
    eff = steel * (1.0 - pl) + film * pl
    # QUENCH pools — near-black glass: the hidden mirror motif (M~205-252 on
    # these exact pixels). Faint dark ring hints keep them reading as oil.
    qcol = _opt_oklch_ramp([(0.008, 0.010, 0.015), (0.026, 0.030, 0.042), (0.052, 0.060, 0.080)],
                           frac_q, flatten_lightness=0.25)
    pq = (pres_q * 0.92)[..., None]
    eff = eff * (1.0 - pq) + qcol * pq
    # forge-heat kiss: the ember corona barely warms the albedo (Cc owns it)
    eff = np.clip(eff + (ember_q * 0.07)[..., None] * np.array([1.0, 0.58, 0.26], np.float32),
                  0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# --- IGNITION: fable_prism_veil ---
# ============================================================================
# ===== FABLE: PRISM VEIL — IGNITION REBUILD (round 4, the Wovenlight law) ===
# The veil is reborn as luminous orchid SILK: a smooth multi-angle thickness
# drape walks the body from deep garnet through orchid-rose up to ice-opal
# crests, with four families of hair-fine wavy silk fibres riding the drape.
# IGNITION — "the ghost filaments": two extra fibre families live ONLY inside
# winding drape-phase corridors. In the albedo they read as faint near-black
# violet hairlines threading the bright silk — but those exact pixels carry
# M~250. Invisible at most angles; when the sun lines up, the veil tears open
# in white-hot prismatic filament streaks against calm satin.
# Aspects of ONE system (decorrelation by aspect, never alien geometry):
#   M  = ghost filaments detonating + soft drape-weighted fibre gleam
#   R  = drape-order boundary corridors (rough seams) + fibre striation
#   Cc = phase-offset sheen pools of the same drape + wet halo on filaments
# UV-agnostic: every axis random, isotropic noise warps, no upright geometry.
# Paint mean luminance lands far above the 0.06 floor (owner round-3 fix).
# ============================================================================


@_memo_fields
def _prism_veil_ign_fields(h, w, seed):
    """ONE generator feeds paint AND spec (spec marries paint).
    Returns (drape, fibre, ghost, corridor, pool, glint), all float32 HxW."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    yy, xx, _, _ = _coords(h, w)
    mx = float(max(h, w))
    sr = mx / 1024.0
    # the drape: smooth multi-angle thickness field that walks the hue
    # (one long + two shorter unequal wavelengths so no moire ellipse lattice)
    drape = np.zeros((h, w), np.float32)
    for spread in (1.9, 1.0, 0.55):
        ang = float(rng.uniform(0.0, 2.0 * np.pi))
        wl = float(rng.uniform(0.09, 0.15)) * spread * mx
        ph = np.float32(rng.uniform(0.0, 2.0 * np.pi))
        drape += (np.sin((xx * np.float32(np.cos(ang) * 2.0 * np.pi / wl)
                          + yy * np.float32(np.sin(ang) * 2.0 * np.pi / wl)) + ph)
                  * np.float32(rng.uniform(0.6, 1.0)))
    drape += (_msc(h, w, [max(31, int(127 * sr)), max(71, int(283 * sr))], seed ^ 0x9A01) - 0.5) * 1.6
    drape = ((drape - drape.min()) / max(float(drape.max() - drape.min()), 1e-6)).astype(np.float32)
    # two shared undulation fields -> every fibre family gets its OWN mix
    warp_a = (_msc(h, w, [max(7, int(36 * sr)), max(13, int(96 * sr))], seed ^ 0x9A11) - 0.5) * 7.5
    warp_b = (_msc(h, w, [max(7, int(44 * sr)), max(15, int(118 * sr))], seed ^ 0x9A12) - 0.5) * 7.5
    # the silk fibres: 4 random-angle hair-fine wavy families (~10-18px @2048)
    fibre = np.zeros((h, w), np.float32)
    for _k in range(4):
        ang = float(rng.uniform(0.0, np.pi))
        per = max(4.0, float(rng.uniform(0.0040, 0.0070)) * mx)
        mixc = float(rng.uniform(0.0, 2.0 * np.pi))
        wp = warp_a * np.float32(np.cos(mixc)) + warp_b * np.float32(np.sin(mixc))
        tri = np.float32(0.5) + np.float32(0.5) * np.sin(
            xx * np.float32(np.cos(ang) * 2.0 * np.pi / per)
            + yy * np.float32(np.sin(ang) * 2.0 * np.pi / per)
            + np.float32(rng.uniform(0.0, 2.0 * np.pi)) + wp)
        t2 = tri * tri
        fibre += (t2 * t2 * t2) * np.float32(rng.uniform(0.7, 1.0))  # tri**6
    fibre = np.clip(fibre, 0.0, 1.0).astype(np.float32)
    # ignition gates: winding drape-phase corridors (two committed bands)
    igate = np.maximum(np.clip(1.0 - np.abs(drape - 0.60) / 0.19, 0.0, 1.0),
                       0.85 * np.clip(1.0 - np.abs(drape - 0.21) / 0.13, 0.0, 1.0)).astype(np.float32)
    # the ghost filaments: 2 extra families ALIVE only inside the gates
    ghost = np.zeros((h, w), np.float32)
    for _k in range(2):
        ang = float(rng.uniform(0.0, np.pi))
        per = max(5.0, float(rng.uniform(0.0068, 0.0112)) * mx)
        mixc = float(rng.uniform(0.0, 2.0 * np.pi))
        wp = warp_a * np.float32(np.sin(mixc)) - warp_b * np.float32(np.cos(mixc))
        tri = np.float32(0.5) + np.float32(0.5) * np.sin(
            xx * np.float32(np.cos(ang) * 2.0 * np.pi / per)
            + yy * np.float32(np.sin(ang) * 2.0 * np.pi / per)
            + np.float32(rng.uniform(0.0, 2.0 * np.pi)) + wp)
        t2 = tri * tri
        ghost = np.maximum(ghost, t2 * t2 * t2 * tri)  # tri**7
    ghost = np.clip(ghost * igate * 1.6 - 0.12, 0.0, 1.0).astype(np.float32)
    # R's own aspect: corridors hugging the quantized drape-order boundaries
    d6 = drape * np.float32(6.0)
    frac = np.abs(d6 - np.round(d6)) * np.float32(2.0)  # 0 at an order line
    c0 = np.clip(np.float32(1.0) - frac / np.float32(0.34), 0.0, 1.0)
    corridor = (c0 * np.sqrt(c0)).astype(np.float32)  # ** 1.5
    # Cc's own aspect: phase-offset sheen pools of the SAME drape
    p0 = np.float32(0.5) + np.float32(0.5) * np.sin(drape * np.float32(2.0 * np.pi * 1.7)
                                                    + np.float32(2.0 * np.pi * 0.31))
    pool = (p0 * p0 * np.sqrt(p0)).astype(np.float32)  # ** 2.5 sheen squeeze
    # micro glint carrier
    glint = _msc(h, w, [2, 4], seed ^ 0x9A31).astype(np.float32)
    return drape, fibre, ghost, corridor, pool, glint


def _spec_fable_prism_veil(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of("fable_prism_veil", seed)
    drape, fibre, ghost, corridor, pool, glint = _prism_veil_ign_fields(h, w, s)
    # M — THE DETONATOR: the ghost filaments (faint dark hairlines in the
    # paint) slam to ~250 on those exact pixels; the silk keeps a calm gleam.
    M = 26.0 + 58.0 * fibre * (0.5 + 0.5 * drape) + 16.0 * (glint - 0.5) + 224.0 * ghost
    # R — its own aspect: drape-order boundary corridors run rough seams
    # across glassy silk; fibre striation rides inside; filaments polish R.
    R = 84.0 + 122.0 * corridor + 30.0 * (fibre - 0.5) - 36.0 * ghost + 16.0 * (glint - 0.5)
    # Cc — its own aspect: wandering sheen pools + a wet halo hugging the
    # filaments so the detonation keeps glass support as the sun walks off.
    halo = cv2.GaussianBlur(ghost, (0, 0), 2.2)
    Cc = 44.0 + 142.0 * pool + 58.0 * halo + 12.0 * (glint - 0.5)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_prism_veil(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of("fable_prism_veil", seed)
    drape, fibre, ghost, corridor, pool, glint = _prism_veil_ign_fields(h, w, s)
    # luminous prismatic silk: the ramp WALKS the hue (garnet -> magenta-rose
    # -> violet-orchid -> pale aqua-opal) as the drape thickens; the fibres
    # carry most of the lift so the body reads as threadwork, never blobs.
    # Mean luminance lands FAR above the 0.06 floor (owner round-3 fix).
    t = np.clip(0.10 + 0.34 * drape + 0.42 * fibre + 0.10 * (glint - 0.5), 0.0, 1.0)
    silk = _opt_oklch_ramp([(0.165, 0.040, 0.100), (0.55, 0.13, 0.36),
                            (0.55, 0.35, 0.78), (0.80, 0.93, 0.92)],
                           t, flatten_lightness=0.12)
    # sheen pools breathe softly; order-boundary seams take a cool press so
    # R's geometry is married into the paint too
    silk = silk * (0.92 + 0.14 * pool[..., None]) * (1.0 - 0.14 * corridor[..., None])
    # THE SECRET: the ghost filaments drop to near-black violet hairlines in
    # the albedo while carrying M~250 — the veil tears open in the sun.
    ink = _opt_oklch_ramp([(0.050, 0.022, 0.095), (0.115, 0.055, 0.180)],
                          drape, flatten_lightness=0.3)
    gv = ghost[..., None]
    eff = np.clip(silk * (1.0 - 0.80 * gv) + ink * (0.80 * gv), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# --- IGNITION: fable_quicksilver_garden ---
# ============================================================================
# FABLE #15 - QUICKSILVER GARDEN (fable_quicksilver_garden) - IGNITION REBUILD
# Round-3 verdict: 'plenty of colors but not dynamic - needs COOL FEATURES.'
# Wovenlight-principle choreography, one fields fn feeds paint AND spec:
# the pastel micro-garden stays (5200 candy cells, silver rim web, silk
# striation bands), but ~1 cell in 6 is now a MERCURY POND - near-black
# liquid glass in the albedo with M~250 on those exact pixels. Dead quiet
# at most angles, the ponds DETONATE into white liquid mirror when the sun
# lines up while the garden idles at calm satin. Cc traces the bright
# silver rim web as wet flash lines; R rides the silk striation lanes the
# candy depth makes visible inside every pastel cell.
# ============================================================================

_quicksilver_garden_ign_cache = {}


def _quicksilver_garden_ign_fields(h, w, seed):
    # shared geometry: (tcell, interior, rim, band, core, merc, owner, n)
    key = (int(h), int(w), int(seed))
    hit = _quicksilver_garden_ign_cache.get(key)
    if hit is not None:
        return hit
    m = float(max(h, w))
    yy, xx, _, _ = _coords(h, w)
    n = 9000
    rng = np.random.default_rng((seed ^ 0x15E801) & 0x7FFFFFFF)
    sy = rng.uniform(0, h, n).astype(np.float32)
    sx = rng.uniform(0, w, n).astype(np.float32)
    cang = rng.uniform(0.0, 2.0 * np.pi, n).astype(np.float32)
    crad = (np.sqrt(h * w / float(n)) * rng.uniform(0.78, 1.28, n)).astype(np.float32)
    toff = rng.uniform(0.0, 0.62, n).astype(np.float32)
    nb = rng.integers(2, 5, n).astype(np.float32)
    merc_lut = (rng.random(n) < 0.16).astype(np.float32)   # the mercury ponds
    wy = (_msc(h, w, [max(int(m * 0.008), 3), max(int(m * 0.03), 5)], seed ^ 0x15E902) - 0.5) * (m * 0.012)
    wx = (_msc(h, w, [max(int(m * 0.008), 3), max(int(m * 0.03), 5)], seed ^ 0x15EA03) - 0.5) * (m * 0.012)
    yyw = yy + wy
    xxw = xx + wx
    d1, d2, owner = _opt_voro_top2(yyw, xxw, sy, sx)
    d1 = np.sqrt(d1)
    d2 = np.sqrt(d2)
    border = d2 - d1
    rim = np.exp(-((border / max(m * 0.0009, 0.8)) ** 2)).astype(np.float32)
    interior = np.clip(border / (m * 0.0045), 0.0, 1.0)
    interior = (interior * interior * (3.0 - 2.0 * interior)).astype(np.float32)
    am = cang[owner]
    rm = np.maximum(crad[owner], 1.0)
    proj = ((xxw - sx[owner]) * np.cos(am) + (yyw - sy[owner]) * np.sin(am)) / rm
    tcell = np.clip(toff[owner] + 0.38 * np.clip(0.5 + 0.5 * proj, 0.0, 1.0), 0.0, 1.0).astype(np.float32)
    band = (0.5 + 0.5 * np.cos(np.pi * 6.0 * nb[owner] * proj)).astype(np.float32)
    core = np.clip(1.0 - d1 / rm, 0.0, 1.0).astype(np.float32)
    merc = merc_lut[owner].astype(np.float32)
    out = (tcell, interior, rim, band, core, merc, owner, n)
    if len(_quicksilver_garden_ign_cache) >= 4:
        _quicksilver_garden_ign_cache.pop(next(iter(_quicksilver_garden_ign_cache)))
    _quicksilver_garden_ign_cache[key] = out
    return out


def _spec_fable_quicksilver_garden(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of('fable_quicksilver_garden', seed)
    tcell, interior, rim, band, core, merc, owner, n = _quicksilver_garden_ign_fields(h, w, s)
    m = float(max(h, w))
    rng = np.random.default_rng((s ^ 0x15EB04) & 0x7FFFFFFF)
    gloss = rng.uniform(0.55, 1.00, n).astype(np.float32)   # per-cell silk depth
    micro = _msc(h, w, [2, max(int(m * 0.005), 3)], s ^ 0x15EC05)
    slow = _msc(h, w, [max(int(m * 0.08), 9), max(int(m * 0.20), 13)], s ^ 0x15ED06)
    # M - IGNITION: the mercury ponds (near-black glass in the paint)
    # detonate to liquid mirror on the SAME pixels; pastel cells idle at a
    # calm satin floor; rims stay dark so Cc owns the web.
    M = 30.0 + 224.0 * merc * interior * (0.90 + 0.10 * core) + 18.0 * (1.0 - merc) * interior
    # R - silk striation lanes: the same bands the candy depth shows in the
    # albedo swing glossy/dull per cell; the ponds go dead-smooth mirror.
    R = (152.0 - 98.0 * band * gloss[owner] * (1.0 - merc) - 104.0 * merc * core
         + 26.0 * rim + 12.0 * (micro - 0.5))
    # Cc - the silver rim web the paint draws flashes WET (traced hot lines),
    # breathing with its own slow third sheen field.
    Cc = 54.0 + 182.0 * (rim ** 0.9) + 26.0 * (slow - 0.5)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_quicksilver_garden(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of('fable_quicksilver_garden', seed)
    tcell, interior, rim, band, core, merc, owner, n = _quicksilver_garden_ign_fields(h, w, s)
    m = float(max(h, w))
    # liquid chrome bed: fine caustic light + a quiet slow breath
    cff = _msc(h, w, [2, 5], s ^ 0x15EE07)
    cfs = _msc(h, w, [max(int(m * 0.06), 7), max(int(m * 0.14), 9)], s ^ 0x15EF08)
    cl = 0.40 + 0.40 * cff ** 1.5 + 0.22 * np.clip((cff - 0.84) / 0.08, 0.0, 1.0) + 0.06 * (cfs - 0.5)
    chrome = np.clip(cl[:, :, None] * np.array([0.94, 0.985, 1.05], np.float32), 0.0, 1.0)
    # pastel garden: per-cell oriented mini-ramps; striation bands feed the
    # candy depth so the silk lanes R lights are VISIBLE in the albedo
    stops = [(0.58, 0.93, 0.78), (0.55, 0.78, 0.96), (0.78, 0.62, 0.93),
             (0.96, 0.62, 0.72), (0.98, 0.88, 0.55)]
    pastel = _opt_oklch_ramp(stops, tcell, flatten_lightness=0.72)
    depth = (interior * (0.24 + 0.34 * core + 0.32 * band)).astype(np.float32)
    eff = candy_absorb(chrome, pastel, depth, density=1.0)
    # MERCURY PONDS: ~1 cell in 6 swaps to near-black liquid glass with a
    # faint meniscus edge-light - the dark half of the ignition (spec M~250
    # detonates these exact pixels).
    t_m = np.clip(0.20 + 0.46 * core + 0.20 * (cfs - 0.5) + 0.12 * (1.0 - interior), 0.0, 1.0)
    pond = _opt_oklch_ramp([(0.016, 0.020, 0.030), (0.046, 0.054, 0.072), (0.105, 0.120, 0.145)],
                           t_m, flatten_lightness=0.25)
    mk = merc[:, :, None]
    eff = eff * (1.0 - mk) + pond * mk
    # the keeper: white-hot silver web outlining every cell (Cc flashes it wet)
    riml = ((rim ** 1.1) * 0.85)[:, :, None]
    eff = eff * (1.0 - riml) + np.array([0.97, 0.985, 1.0], np.float32) * riml
    grain = _msc(h, w, [2, max(int(m * 0.004), 2)], s ^ 0x15F009)
    eff = np.clip(eff * (0.94 + 0.10 * grain[:, :, None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


# --- IGNITION: fable_saffron_circuit ---
# ============================================================================
# ===== FABLE: SAFFRON CIRCUIT — IGNITION REBUILD (2026-06-10 round 4) =======
# Wovenlight principle: ONE shared circuit-board geometry feeds paint AND
# spec. ~270 scattered trace runs with 45/90-degree elbows at random angles
# (UV-agnostic, never a grid); ~45% are HOT POWER RAILS drawn as vivid
# scarlet-ember lines in the albedo — and those EXACT pixels detonate M ~252
# so the red lines flash as hot spots the instant the sun lines up. The cool
# saffron service traces stay engraved and calm. Aspect split: M = hot-rail
# cores ONLY; R = inverse etch relief of the FULL trace lattice + flank
# corridors; Cc = solder-pad blooms + a third-angle sheen pool. Color is
# seasoning: saffron->rose->ember density ramp, scarlet rails, amber pads.
# ============================================================================


@_memo_fields
def _saffron_circuit_ign_fields(h, w, seed):
    """Shared geometry for paint AND spec (spec marries paint).
    Returns (hotcore, coolink, etch, flank, via, viahalo, density, sheen)."""
    m = float(max(h, w))
    sr = m / 1024.0
    rng = np.random.default_rng((seed ^ 0x5AF14C) & 0x7FFFFFFF)
    hot8 = np.zeros((h, w), np.uint8)
    cool8 = np.zeros((h, w), np.uint8)
    for _ in range(1000):  # scatter placement loop — every trace its own pos/angle
        x0 = float(rng.uniform(0.0, w))
        y0 = float(rng.uniform(0.0, h))
        ang = float(rng.uniform(0.0, 2.0 * np.pi))
        ln = float(rng.uniform(0.024, 0.085)) * m
        th = max(2, int(round(float(rng.uniform(0.0016, 0.0036)) * m)))
        is_hot = bool(rng.random() < 0.45)
        if is_hot:
            th = max(3, int(round(th * 2.2)))  # power rails run heavier
        tgt = hot8 if is_hot else cool8
        x1 = x0 + float(np.cos(ang)) * ln
        y1 = y0 + float(np.sin(ang)) * ln
        cv2.line(tgt, (int(x0), int(y0)), (int(x1), int(y1)), 255, th, cv2.LINE_AA)
        if rng.random() < 0.65:  # circuit elbow in the trace's own frame
            bend = ang + float(rng.choice((-1.0, 1.0))) * float(rng.choice((np.pi / 4.0, np.pi / 2.0)))
            l2 = float(rng.uniform(0.016, 0.060)) * m
            x2 = x1 + float(np.cos(bend)) * l2
            y2 = y1 + float(np.sin(bend)) * l2
            cv2.line(tgt, (int(x1), int(y1)), (int(x2), int(y2)), 255, th, cv2.LINE_AA)
    hot = hot8.astype(np.float32) / 255.0
    coolink = (cool8.astype(np.float32) / 255.0)
    hotcore = np.clip(hot * 1.3, 0.0, 1.0).astype(np.float32)
    ink = np.maximum(hot, coolink)
    # groove relief of the FULL lattice with slow depth modulation (R aspect)
    depth_mod = _msc(h, w, [max(int(m * 0.07), 7), max(int(m * 0.20), 13)], seed ^ 0x5AF2B1)
    etch = cv2.GaussianBlur(ink, (0, 0), max(0.7, m * 0.0010))
    etch = np.clip(etch * (0.55 + 0.45 * depth_mod), 0.0, 1.0).astype(np.float32)
    # flank corridors hugging every trace edge (R's second aspect)
    spread = cv2.GaussianBlur(ink, (0, 0), max(1.5, m * 0.0042))
    flank = np.clip(spread * 1.8 - ink * 1.4, 0.0, 1.0).astype(np.float32)
    # solder pads at their OWN scattered points (Cc aspect)
    rng_v = np.random.default_rng((seed ^ 0x5AF3D2) & 0x7FFFFFFF)
    via8 = np.zeros((h, w), np.uint8)
    for _ in range(420):  # scatter placement loop
        cx = int(rng_v.uniform(0, w))
        cy = int(rng_v.uniform(0, h))
        rr = max(2, int(round(float(rng_v.uniform(0.0020, 0.0048)) * m)))
        cv2.circle(via8, (cx, cy), rr, 255, -1, cv2.LINE_AA)
    via = via8.astype(np.float32) / 255.0
    viahalo = cv2.GaussianBlur(via, (0, 0), max(2.0, m * 0.009))
    viahalo = (viahalo / max(float(viahalo.max()), 1e-6)).astype(np.float32)
    # local trace density keys the paint hue ramp (quantile-stretched)
    density = cv2.GaussianBlur(ink, (0, 0), m * 0.017)
    d_lo = float(np.quantile(density, 0.05))
    d_hi = float(np.quantile(density, 0.95))
    density = np.clip((density - d_lo) / max(d_hi - d_lo, 1e-6), 0.0, 1.0).astype(np.float32)
    # third-angle sheen pool (Cc's own slow geometry, domain-warped band)
    yy, xx, _, _ = _coords(h, w)
    a3 = float(rng_v.uniform(0.0, np.pi))
    p3 = max(40.0, float(rng_v.uniform(150.0, 230.0)) * sr)
    w3 = (_msc(h, w, [max(17, int(67 * sr)), max(43, int(171 * sr))], seed ^ 0x5AF4E3) - 0.5) * (38.0 * sr)
    c3 = (xx * np.cos(a3) + yy * np.sin(a3) + w3) / p3
    sheen = ((0.5 + 0.5 * np.sin(2.0 * np.pi * c3)) ** 2.2).astype(np.float32)
    return hotcore, coolink, etch, flank, via, viahalo, density, sheen


def _spec_fable_saffron_circuit(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of("fable_saffron_circuit", seed)
    hotcore, coolink, etch, flank, via, viahalo, density, sheen = _saffron_circuit_ign_fields(h, w, s)
    m = float(max(h, w))
    micro_r = _msc(h, w, [3, max(int(m * 0.010), 4)], s ^ 0x5AF5F4)
    micro_c = _msc(h, w, [2, max(int(m * 0.005), 3)], s ^ 0x5AF605)
    # M — IGNITION: the scarlet power rails detonate on their EXACT paint
    # pixels (~252); everything else holds a calm saffron-satin floor.
    M = np.clip(26.0 + 226.0 * hotcore + 214.0 * via * (1.0 - hotcore)
                + 20.0 * density * (1.0 - hotcore) * (1.0 - via), 0.0, 255.0)
    # R — the FULL-lattice relief: grooves polish glossy (low R), flank
    # corridors run satin-bright; brushed micro keeps the plateau alive.
    R = np.clip(192.0 - 150.0 * etch + 34.0 * flank + 22.0 * (micro_r - 0.5), 12.0, 255.0)
    # Cc — solder-pad blooms + the wandering third-angle sheen pool; the
    # grooves drink a little of the wet clear.
    Cc = np.clip(40.0 + 138.0 * viahalo + 70.0 * via + 30.0 * sheen - 16.0 * etch
                 + 10.0 * (micro_c > 0.92).astype(np.float32), 0.0, 255.0)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_saffron_circuit(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of("fable_saffron_circuit", seed)
    hotcore, coolink, etch, flank, via, viahalo, density, sheen = _saffron_circuit_ign_fields(h, w, s)
    m = float(max(h, w))
    # saffron->rose->ember body keyed to local circuit density (flat-light)
    drift = _msc(h, w, [max(int(m * 0.028), 4), max(int(m * 0.08), 7)], s ^ 0x5AF716)
    t = np.clip(0.78 * density + 0.22 * drift, 0.0, 1.0)
    eff = _opt_oklch_ramp([(0.99, 0.68, 0.16), (0.90, 0.36, 0.30), (0.50, 0.16, 0.10)],
                          t, flatten_lightness=0.55)
    # engrave the cool service traces + grooves (calm copper shadow work)
    shade = (1.0 - 0.34 * coolink) * (1.0 - 0.24 * etch)
    eff = eff * shade[..., None]
    # HOT POWER RAILS: vivid scarlet-ember lines on the EXACT ignition pixels
    heat = _msc(h, w, [max(int(m * 0.012), 3), max(int(m * 0.04), 4)], s ^ 0x5AF827)
    railcol = _opt_oklch_ramp([(0.80, 0.10, 0.06), (1.00, 0.30, 0.10)], heat)
    hc = hotcore[..., None]
    eff = eff * (1.0 - hc) + railcol * hc
    # solder pads glint amber in the paint too (Cc geometry stays married)
    eff = np.clip(eff + (0.30 * via + 0.16 * viahalo)[..., None]
                  * np.array([0.95, 0.62, 0.20], np.float32), 0.0, 1.0)
    # the third-angle pool kisses the albedo (subtle; Cc carries the glow)
    eff = np.clip(eff * (0.93 + 0.13 * sheen[..., None]), 0.0, 1.0)
    grain = _msc(h, w, [2, max(int(m * 0.004), 2)], s ^ 0x5AF938)
    eff = np.clip(eff * (0.94 + 0.10 * grain[..., None]), 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


FABLE_MONOLITHICS.update({
    FAB_14: (_spec_fable_saffron_circuit, _paint_fable_saffron_circuit),
})


# --- IGNITION: fable_static_bloom ---
# ============================================================================
# ===== FABLE: STATIC BLOOM (FAB_12) — IGNITION rebuild 2026-06-10 ===========
# Round-3 owner verdict: spec not following the pattern of the paint well
# enough. Round-4 = the Wovenlight principle: ONE shared field generator
# (_static_bloom_ign_fields) feeds BOTH paint and spec, so every spec feature
# lands on a feature the paint actually draws.
#   * Three interlocking micro territories (organic argmax islands ~16-24px
#     at canvas): cobalt static / magenta filament / amber ember.
#   * GLOBAL signal-static layer from ONE random draw split in two: LIVE pins
#     (bright cyan, cobalt territory) and DEAD dropout pins everywhere —
#     near-black micro holes in the albedo.
#   * IGNITION (M): the dead dropouts and the filaments' white-hot cores —
#     the EXACT dark holes and bright lines the paint shows — detonate at
#     ~235-250 while live pins only gleam and the floor idles at ~30.
#   * R rides a DIFFERENT aspect of the same system: the visible color-
#     territory borders become wet gloss lanes cutting the matte body
#     (filament flanks soften the grain too).
#   * Cc rides the ember aspect: glass glow on the amber blooms + their halo
#     rings, breathing on a slow macro field.
# UV-agnostic: isotropic islands, 3 random filament axes, scattered static
# and embers — nothing upright, nothing centered. Features 8-32px at 2048.
# Fully vectorized (blurred-impulse splats, no per-pixel python loops).
# ============================================================================


@_memo_fields
def _static_bloom_ign_fields(h, w, seed):
    # Shared geometry for paint AND spec — the marriage contract.
    m = float(max(h, w))
    sr = m / 1024.0
    yy, xx, _, _ = _coords(h, w)
    # --- interlocking micro territories: argmax of three blurred noises ---
    rt = np.random.default_rng((seed ^ 0x5AB10C) & 0x7FFFFFFF)
    sig = max(1.4, 2.0 * sr)
    f0 = cv2.GaussianBlur(rt.random((h, w)).astype(np.float32), (0, 0), sig)
    f1 = cv2.GaussianBlur(rt.random((h, w)).astype(np.float32), (0, 0), sig)
    f2 = cv2.GaussianBlur(rt.random((h, w)).astype(np.float32), (0, 0), sig)
    am = np.argmax(np.stack([f0, f1, f2], axis=0), axis=0)
    msk = [cv2.GaussianBlur((am == c).astype(np.float32), (0, 0), 0.6) for c in range(3)]
    tot = msk[0] + msk[1] + msk[2] + 1e-6
    m0 = (msk[0] / tot).astype(np.float32)
    m1 = (msk[1] / tot).astype(np.float32)
    m2 = (msk[2] / tot).astype(np.float32)
    # territory seam corridors — R's own aspect: the borders the paint shows
    seam = np.clip((1.0 - np.maximum(np.maximum(m0, m1), m2)) * 2.4, 0.0, 1.0).astype(np.float32)
    # --- GLOBAL signal static: ONE draw split into LIVE and DEAD pins ---
    rs = np.random.default_rng((seed ^ 0x6BC21D) & 0x7FFFFFFF)
    base = rs.random((h, w)).astype(np.float32)
    dens = _msc(h, w, [max(17, int(61 * sr)), max(43, int(151 * sr))],
                seed ^ 0x7CD32E).astype(np.float32)
    thr = 0.930 - 0.035 * dens
    live = (base > thr).astype(np.float32)
    dead = ((base > thr - 0.050) & (base <= thr)).astype(np.float32)
    live = np.clip(cv2.GaussianBlur(live, (0, 0), max(0.45, 0.55 * sr)) * 2.6,
                   0.0, 1.0).astype(np.float32)
    dead = np.clip(cv2.GaussianBlur(dead, (0, 0), max(0.50, 0.62 * sr)) * 2.8,
                   0.0, 1.0).astype(np.float32)
    # --- micro filaments on THREE random axes: broad body + white-hot core ---
    rf = np.random.default_rng((seed ^ 0x8DE43F) & 0x7FFFFFFF)
    wpx = (_msc(h, w, [max(5, int(17 * sr)), max(13, int(47 * sr))],
                seed ^ 0x9EF540) - 0.5) * (9.0 * sr)
    fil = np.zeros((h, w), np.float32)
    fhot = np.zeros((h, w), np.float32)
    for _ in range(3):
        ang = rf.uniform(0.0, np.pi)
        per = max(2.4, rf.uniform(3.0, 4.5) * sr)
        ph = (xx * np.cos(ang) + yy * np.sin(ang) + wpx * rf.uniform(0.6, 1.2)) / per
        ridge = (1.0 - np.abs(np.sin(np.pi * ph))).astype(np.float32)
        fil = np.maximum(fil, ridge ** 2.2)
        fhot = np.maximum(fhot, ridge ** 6.0)
    # --- amber embers: blurred-impulse splats + halo ring aspect ---
    re_ = np.random.default_rng((seed ^ 0xA1B651) & 0x7FFFFFFF)
    n_emb = max(850, int(3400 * sr * sr))
    eyc = re_.integers(0, h, n_emb)
    exc = re_.integers(0, w, n_emb)
    amp = re_.uniform(0.5, 1.0, n_emb).astype(np.float32)
    imp = np.zeros((h, w), np.float32)
    np.add.at(imp, (eyc, exc), amp)
    bn = cv2.GaussianBlur(imp, (0, 0), max(0.9, 1.1 * sr))
    bw = cv2.GaussianBlur(imp, (0, 0), max(2.0, 2.6 * sr))
    bloom = np.clip(bn * 7.0, 0.0, 1.0).astype(np.float32)
    ring = np.clip(bw * 16.0 - bn * 5.0, 0.0, 1.0).astype(np.float32)
    return m0, m1, m2, live, dead, fil, fhot, bloom, ring, seam, dens


def _spec_fable_static_bloom(shape, mask, seed, sm):
    h, w, _ = _work_shape(shape)
    fh, fw = _shape2(shape)
    s = _seed_of('fable_static_bloom', seed)
    (m0, m1, m2, live, dead, fil, fhot, bloom, ring,
     seam, dens) = _static_bloom_ign_fields(h, w, s)
    g1 = np.random.default_rng((s ^ 0x4A1F62) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    g2 = np.random.default_rng((s ^ 0x5B2E73) & 0x7FFFFFFF).random((h, w)).astype(np.float32)
    sr = max(h, w) / 1024.0
    cmac = _msc(h, w, [max(37, int(131 * sr)), max(83, int(293 * sr))],
                s ^ 0x6C3D84).astype(np.float32)
    # M — THE DETONATOR: the paint's near-black dropout pins (global) and the
    # filaments' white-hot cores (magenta territory) hit ~235-250 on the SAME
    # pixels the paint draws them; bright cyan live pins only gleam; the
    # floor idles dark and calm (hot >200 area ~7-10%).
    M = 26.0 + 8.0 * (g1 - 0.5) + 36.0 * live * m0 + 240.0 * fhot * m1 + 88.0 * dead
    # R — its own aspect of the same system: the visible color-territory
    # borders are wet gloss lanes cutting the matte body; filament flanks
    # soften the grain inside the magenta islands.
    R = 180.0 - 142.0 * seam - 34.0 * fil * m1 + 18.0 * (g2 - 0.5)
    # Cc — the ember aspect: glass glow pooled on the amber blooms and their
    # halo rings, breathing on a slow macro field everywhere else.
    Cc = 46.0 + 175.0 * bloom * m2 + 70.0 * ring * m2 + 20.0 * (cmac - 0.5)
    M, R, Cc = (_upscale(a.astype(np.float32), fh, fw) for a in (M, R, Cc))
    return _pack_spec(M, R, Cc, _mask2(mask, fh, fw), sm, fh, fw)


def _paint_fable_static_bloom(paint, shape, mask, seed, pm, bb):
    fh, fw = _shape2(shape)
    h, w, _ = _work_shape(shape)
    s = _seed_of('fable_static_bloom', seed)
    (m0, m1, m2, live, dead, fil, fhot, bloom, ring,
     seam, dens) = _static_bloom_ign_fields(h, w, s)
    # territory 0 — electric cobalt static: LIVE pins flare bright cyan out
    # of deep navy-black
    t0 = np.clip(0.15 + 0.60 * live + 0.20 * (dens - 0.5), 0.0, 1.0)
    col0 = _opt_oklch_ramp([(0.008, 0.018, 0.085), (0.060, 0.210, 0.500), (0.350, 0.880, 1.000)],
                           t0, flatten_lightness=0.1)
    # territory 1 — magenta filaments with white-hot cores (the EXACT lines
    # the M channel detonates)
    t1 = np.clip(0.12 + 0.52 * fil + 0.33 * fhot, 0.0, 1.0)
    col1 = _opt_oklch_ramp([(0.150, 0.025, 0.130), (0.560, 0.090, 0.480), (1.000, 0.640, 0.950)],
                           t1, flatten_lightness=0.1)
    # territory 2 — amber embers + faint halo rings out of deep maroon (the
    # EXACT glow the Cc channel coats in glass)
    t2 = np.clip(0.10 + 0.74 * bloom + 0.22 * ring, 0.0, 1.0)
    col2 = _opt_oklch_ramp([(0.190, 0.055, 0.035), (0.660, 0.280, 0.095), (1.000, 0.780, 0.420)],
                           t2, flatten_lightness=0.1)
    eff = col0 * m0[..., None] + col1 * m1[..., None] + col2 * m2[..., None]
    # GLOBAL dead-pixel dropouts: near-black holes punched in the static —
    # quiet promises the M channel cashes when the sun lines up
    eff = eff * (1.0 - 0.58 * dead)[..., None]
    # seam corridors ink the territory borders (the R gloss lanes)
    eff = eff * (1.0 - 0.30 * seam)[..., None]
    # macro density carrier + territory luminance tiers keep the micro grain
    # readable at car distance (cobalt deepest, amber brightest)
    tier = (0.86 + 0.22 * m2 + 0.09 * m1).astype(np.float32)
    eff = np.clip(eff * ((0.80 + 0.22 * dens) * tier)[..., None], 0.0, 1.0).astype(np.float32)
    eff = _upscale(eff, fh, fw)
    return _blend_paint(paint, eff, _mask2(mask, fh, fw), pm)


FABLE_MONOLITHICS.update({
    "fable_comet_parade": (_spec_fable_comet_parade, _paint_fable_comet_parade),
    "fable_magnetite_flow": (_spec_fable_magnetite_flow, _paint_fable_magnetite_flow),
    "fable_nightbloom": (_spec_fable_nightbloom, _paint_fable_nightbloom),
    "fable_oilforge": (_spec_fable_oilforge, _paint_fable_oilforge),
    "fable_prism_veil": (_spec_fable_prism_veil, _paint_fable_prism_veil),
    "fable_quicksilver_garden": (_spec_fable_quicksilver_garden, _paint_fable_quicksilver_garden),
    "fable_saffron_circuit": (_spec_fable_saffron_circuit, _paint_fable_saffron_circuit),
    "fable_static_bloom": (_spec_fable_static_bloom, _paint_fable_static_bloom),
})
# === IGNITION REBUILD 2026-06-10 END ===


# === IGN CALIB 2026-06-10 START ===

def _ign_knee_packed(fn, ch, t_pct=92.0):
    """LEDGE remap: pixels above the t_pct percentile land on 210-255 (guaranteed
    ignition); an over-bright sub-ledge body is scaled under 195 for calm."""
    def f(shape, mask, seed, sm, _f=fn, _c=ch, _t=t_pct):
        import numpy as _np
        out = _f(shape, mask, seed, sm)
        c = out[:, :, _c].astype(_np.float32)
        # deterministic micro-dither breaks ties so flat-bright channels still
        # ledge their top 8% (reads as fine metal-flake sparkle, not a wall)
        c = c + _np.random.default_rng(0x1D17).random(c.shape).astype(_np.float32)
        sel = out[:, :, 3] > 0
        t = float(_np.percentile(c[sel] if sel.any() else c, _t))
        cmax = float(c.max())
        low = c * (195.0 / t) if t > 195.0 else c
        hi = 210.0 + 45.0 * (c - t) / max(1e-3, cmax - t)
        out[:, :, _c] = _np.clip(_np.where(c >= t, hi, low), 0, 255).astype(_np.uint8)
        return out
    return f


def _ign_crush_paint(fn, amp=0.50):
    """SHARP-edged 4-8px micro-fleck layer multiplied into the painted region —
    hard transitions carry the fine gradient energy the fineness metric reads
    (smooth grain does not move it)."""
    def f(paint, shape, mask, seed, pm, bb, _f=fn, _a=amp):
        import numpy as _np
        out = _f(paint, shape, mask, seed, pm, bb)
        fh, fw = _shape2(shape)
        wh, ww = min(fh, 1024), min(fw, 1024)
        g = _np.asarray(_msc(wh, ww, [2, 4], (int(seed) ^ 0xC4C4C4) & 0x7FFFFFFF), _np.float32)
        fleck = _np.clip((g - 0.42) * 5.0, 0.0, 1.0)
        fleck = _upscale(fleck, fh, fw)
        mk = _mask2(mask, fh, fw)
        mod = 1.0 + (fleck - float(fleck.mean())) * _a * mk
        out = _np.clip(_np.asarray(out, _np.float32) * mod[..., None], 0.0, 1.0)
        return out.astype(_np.float32)
    return f


FABLE_MONOLITHICS["fable_saffron_circuit"] = (FABLE_MONOLITHICS["fable_saffron_circuit"][0], _ign_crush_paint(FABLE_MONOLITHICS["fable_saffron_circuit"][1], 0.5))

FABLE_MONOLITHICS["fable_saffron_circuit"] = (_ign_knee_packed(FABLE_MONOLITHICS["fable_saffron_circuit"][0], 2), FABLE_MONOLITHICS["fable_saffron_circuit"][1])

FABLE_MONOLITHICS["fable_oilforge"] = (FABLE_MONOLITHICS["fable_oilforge"][0], _ign_crush_paint(FABLE_MONOLITHICS["fable_oilforge"][1], 0.5))

FABLE_MONOLITHICS["fable_quicksilver_garden"] = (FABLE_MONOLITHICS["fable_quicksilver_garden"][0], _ign_crush_paint(FABLE_MONOLITHICS["fable_quicksilver_garden"][1], 0.5))

FABLE_MONOLITHICS["fable_nightbloom"] = (FABLE_MONOLITHICS["fable_nightbloom"][0], _ign_crush_paint(FABLE_MONOLITHICS["fable_nightbloom"][1], 0.5))

FABLE_MONOLITHICS["fable_magnetite_flow"] = (FABLE_MONOLITHICS["fable_magnetite_flow"][0], _ign_crush_paint(FABLE_MONOLITHICS["fable_magnetite_flow"][1], 0.5))

FABLE_MONOLITHICS["fable_comet_parade"] = (FABLE_MONOLITHICS["fable_comet_parade"][0], _ign_crush_paint(FABLE_MONOLITHICS["fable_comet_parade"][1], 0.5))

FABLE_MONOLITHICS["fable_static_bloom"] = (_ign_knee_packed(FABLE_MONOLITHICS["fable_static_bloom"][0], 0), FABLE_MONOLITHICS["fable_static_bloom"][1])
# === IGN CALIB 2026-06-10 END ===
