"""SHOKKER Living Finishes.

Static iRacing textures cannot literally animate, so this pack builds
"phase-field" materials: paint color, metallic, roughness, and clearcoat are
offset from each other so the finish appears to move when the car, camera, or
lighting moves.

`living_motion_overlay` adds multi-axis anisotropic beats (misaligned M/R/Cc)
for maximum highlight crawl — shared by all finishes in this module (and
imported by `living_chrome` in paradigm).

**Performance (category-wide):** See `_LIVING_*` caps at top of file — field
downsample (`_fast_field_from` + per-finish `_*_core`), electric work buffer,
half-res motion overlay / triplet on large outputs. End-to-end render time also
depends on host resolution, I/O, and app pipeline outside this module.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import numpy as np

from engine.core import _resize_array, get_mgrid, hsv_to_rgb_vec, multi_scale_noise


_FIELD_CACHE: dict[tuple[str, tuple[int, int], int], np.ndarray] = {}

# SPB perf 2026-06-13 (living_finishes lane): the per-pixel channel-build math (dozens of
# fused multiply-add + clip + sin/exp lines on full-res arrays) is the dominant render cost
# and is irreducible at native resolution — downsampling visibly softens the thin specular
# ridges these finishes depend on. NumPy ufuncs release the GIL, so we run the *purely
# elementwise* body across horizontal row-bands on a shared thread pool. This is
# bit-identical (each band computes the same float ops on its own rows; results are
# re-stacked) and uses otherwise-idle cores. Only seam-free elementwise work is banded;
# neighbour-dependent steps (np.diff edges, field generation, resizes, motion overlay)
# stay on full arrays. See _NIGHTLY/perf_fix/living_finishes.py for the equivalence proofs.
_LIVING_BAND_MIN_SIDE = 640  # only band when the output is large enough to amortise thread overhead
_LIVING_BAND_COUNT = min(8, max(1, (os.cpu_count() or 4)))


def _living_bands(h: int, n: int):
    edges = np.linspace(0, h, n + 1).astype(int)
    return [(int(edges[i]), int(edges[i + 1])) for i in range(n) if edges[i + 1] > edges[i]]


# Lazily-created shared pool (avoids a per-call pool; threads are cheap and reused).
_LIVING_POOL = None


def _get_living_pool():
    global _LIVING_POOL
    if _LIVING_POOL is None:
        _LIVING_POOL = ThreadPoolExecutor(
            max_workers=_LIVING_BAND_COUNT, thread_name_prefix="living"
        )
    return _LIVING_POOL


def _slice_band(a, r0, r1, h):
    """Slice the band rows from ``a`` unless ``a`` is a broadcastable constant (first axis
    length != full height, e.g. a (3,) RGB color or a (1,1,C) scalar), which is passed
    through unchanged so NumPy broadcasting still applies per band."""
    arr = np.asarray(a)
    if arr.ndim >= 1 and arr.shape[0] == h:
        return arr[r0:r1]
    return a


def _band_channels(shape, inputs, body, n_bands=None):
    """Run a purely-elementwise ``body`` over horizontal row-bands and re-stack.

    ``inputs`` is a tuple of full-res 2D float32 arrays (already computed, seam-sensitive
    work done). ``body(*band_slices) -> (m_band, r_band, cc_band)`` must be elementwise
    (no np.diff / resize / cross-row ops) so banding is bit-identical to the full-array call.
    Falls back to a single full-array call for small outputs or when bands == 1.
    """
    h, w = shape
    if n_bands is None:
        n_bands = _LIVING_BAND_COUNT
    if max(h, w) < _LIVING_BAND_MIN_SIDE or n_bands <= 1:
        return body(*inputs)
    bands = _living_bands(h, n_bands)
    if len(bands) <= 1:
        return body(*inputs)
    results = [None] * len(bands)

    def _run(i):
        r0, r1 = bands[i]
        results[i] = body(*tuple(_slice_band(a, r0, r1, h) for a in inputs))

    list(_get_living_pool().map(_run, range(len(bands))))
    m = np.vstack([res[0] for res in results])
    r = np.vstack([res[1] for res in results])
    cc = np.vstack([res[2] for res in results])
    return m, r, cc


def _band_image(shape, inputs, body, n_bands=None):
    """Like ``_band_channels`` but ``body(*slices) -> single HxWxC array`` (paint effect)."""
    h, w = shape
    if n_bands is None:
        n_bands = _LIVING_BAND_COUNT
    if max(h, w) < _LIVING_BAND_MIN_SIDE or n_bands <= 1:
        return body(*inputs)
    bands = _living_bands(h, n_bands)
    if len(bands) <= 1:
        return body(*inputs)
    results = [None] * len(bands)

    def _run(i):
        r0, r1 = bands[i]
        results[i] = body(*tuple(_slice_band(a, r0, r1, h) for a in inputs))

    list(_get_living_pool().map(_run, range(len(bands))))
    return np.vstack(results)

# Category-wide perf: procedural fields & overlays scale ~ O(pixels). These caps keep quality while
# bounding work (especially 2K–8K previews). Tune here for global speed vs fidelity.
_LIVING_FIELD_FAST_CAP = 544  # max side → downsample field then upscale + grain (all `_fast_field_from`)
_LIVING_ELECTRIC_WORK_CAP = 560  # arc field: always sim at ≤ this max side, upscale (major win vs full-res bolts)
_LIVING_HALF_OVERLAY_MIN = 896  # half-res motion-overlay deltas (living category — cuts ~4× overlay cost when huge)
_LIVING_HALF_TRIPLET_MIN = 1024  # half-res VM-style triplet pass (electric / lake / neon use this hardest)
_LIVING_BRDF_WORK_CAP = 768  # SPB perf 2026-05-31: shared 2K BRDF carriers upscale cleanly from this cap.
_LIVING_MICRO_WORK_CAP = 768  # SPB perf 2026-05-31: preserve pixel-scale line freq on bounded work grids.
_LIVING_LED_WORK_CAP = 1024  # SPB perf 2026-05-31: LED cells preserve scale at 2K after bounded render.


def _norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    mn = float(arr.min())
    mx = float(arr.max())
    if mx <= mn:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - mn) / (mx - mn + 1e-8)).astype(np.float32)


def _mask2(mask, shape):
    if mask is None:
        return np.ones(shape, dtype=np.float32)
    return np.asarray(mask, dtype=np.float32)


def _bb3(bb, shape):
    arr = np.asarray(bb, dtype=np.float32)
    if arr.ndim == 2:
        arr = arr[:, :, np.newaxis]
    if arr.ndim == 0:
        arr = np.full((shape[0], shape[1], 1), float(arr), dtype=np.float32)
    return arr


def _hsv_to_rgb(h, s, v):
    h = np.mod(h, 1.0).astype(np.float32)
    s = np.clip(s, 0.0, 1.0).astype(np.float32)
    v = np.clip(v, 0.0, 1.0).astype(np.float32)
    r, g, b = hsv_to_rgb_vec(h, s, v)
    return np.stack([r, g, b], axis=-1).astype(np.float32)


def _spec_out(shape, mask, m, r, cc):
    mask = _mask2(mask, shape)
    out = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    out[:, :, 0] = np.clip(np.asarray(m, dtype=np.float32) * mask, 0, 255).astype(np.uint8)
    out[:, :, 1] = np.clip(np.asarray(r, dtype=np.float32) * mask, 15, 255).astype(np.uint8)
    out[:, :, 2] = np.clip(np.asarray(cc, dtype=np.float32), 16, 255).astype(np.uint8)
    out[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return out


def _finish_paint(base, effect, mask, pm):
    mask3 = mask[:, :, np.newaxis]
    blend = np.clip(mask3 * float(pm), 0.0, 1.0)
    return np.clip(base * (1.0 - blend) + effect * blend, 0.0, 1.0).astype(np.float32)


def _edge_energy(field, gain=5.5):
    dx = np.abs(np.diff(field, axis=1, prepend=field[:, :1]))
    dy = np.abs(np.diff(field, axis=0, prepend=field[:1, :]))
    return np.clip(np.sqrt(dx * dx + dy * dy) * gain, 0.0, 1.0).astype(np.float32)


@lru_cache(maxsize=4)
def _coords_cached(h, w):
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    yn = yf / max(h - 1, 1)
    xn = xf / max(w - 1, 1)
    return yf, xf, yn, xn


def _coords(shape):
    h, w = shape
    return _coords_cached(int(h), int(w))


@lru_cache(maxsize=64)
def _hash_noise(shape, seed):
    yf, xf, _, _ = _coords(shape)
    raw = np.sin(xf * 12.9898 + yf * 78.233 + float(seed) * 0.137) * 43758.5453
    return (raw - np.floor(raw)).astype(np.float32)


@lru_cache(maxsize=64)
def _micro_line_field_native(shape, seed, angle=0.0, freq=0.40, coord_scale=1.0):
    yf, xf, _, _ = _coords(shape)
    if coord_scale != 1.0:
        inv = 1.0 / max(float(coord_scale), 1e-6)
        yf = yf * inv
        xf = xf * inv
    ca = np.cos(angle)
    sa = np.sin(angle)
    axis = xf * ca + yf * sa
    cross = -xf * sa + yf * ca
    jitter = _hash_noise(shape, seed) * 0.55
    line_a = np.sin(axis * freq + np.sin(cross * 0.031 + seed) * 1.8 + jitter)
    line_b = np.sin(axis * freq * 1.93 + cross * 0.017 + seed * 0.19)
    return _norm01(line_a * 0.62 + line_b * 0.38)


@lru_cache(maxsize=64)
def _micro_line_field(shape, seed, angle=0.0, freq=0.40):
    h, w = shape
    ref_full = float(max(h, w))
    if ref_full <= float(_LIVING_MICRO_WORK_CAP):
        return _micro_line_field_native(shape, seed, angle, freq, 1.0)
    scale = float(_LIVING_MICRO_WORK_CAP) / ref_full
    work_shape = (max(96, int(round(h * scale))), max(96, int(round(w * scale))))
    small = _micro_line_field_native(work_shape, seed, angle, freq, scale)
    up = _resize_array(small, h, w)
    grain = _hash_noise(shape, seed + 9043)
    return _norm01(up * 0.955 + grain * 0.045)


def _living_motion_deltas(shape_work, seed, weight, ref_full: float):
    """Additive M/R/Cc deltas (before `sm`); `ref_full` = max side of final output for stable frequencies.

    Body is purely elementwise (b1..hinge are point functions of the coord grids), EXCEPT the
    `shimmer = _norm01(...)` global min/max. We compute the un-normalised shimmer accumulator
    and its global min/max on full arrays, then fold the exact same normalisation into the
    banded body so the result is bit-identical to the single-array path.
    """
    yf, xf, yn, xn = _coords(shape_work)
    hw, ww = shape_work
    si = int(seed) % (2**31)
    ref = ref_full

    ang = (si % 360) * (np.pi / 180.0)
    ca, sa = np.cos(ang), np.sin(ang)
    ang2 = ang + 2.0943951023931953
    ca2, sa2 = np.cos(ang2), np.sin(ang2)
    ang3 = ang + 4.1887902047863905
    ca3, sa3 = np.cos(ang3), np.sin(ang3)

    su = (28.0 / ref) * (1.0 + (si % 5) * 0.045)
    sv = (26.0 / ref) * (1.0 + (si % 7) * 0.038)
    eff = float(weight)
    cw = float(ww)
    ch = float(hw)

    def _stage1(yf, xf, yn, xn):
        u1 = (xf * ca + yf * sa) * su
        v1 = (-xf * sa + yf * ca) * sv
        u2 = (xf * ca2 + yf * sa2) * su * 1.37
        v2 = (-xf * sa2 + yf * ca2) * sv * 1.29
        u3 = (xf * ca3 + yf * sa3) * su * 0.94
        b1 = np.sin(u1 * 4.1 + np.sin(v1 * 0.52) * 2.4 + si * 0.019)
        b2 = np.cos(u2 * 4.6 - np.sin(v2 * 0.44) * 1.9 + si * 0.027)
        b3 = np.sin((u1 + v2) * 3.4) * np.cos((u2 - v1) * 3.0)
        b4 = np.sin(u3 * 5.2 + yn * 14.0)
        acc = (b1 * 0.34 + b2 * 0.28 + b3 * 0.26 + b4 * 0.12).astype(np.float32)
        return b1, b2, b3, acc

    if max(hw, ww) < _LIVING_BAND_MIN_SIDE:
        b1, b2, b3, acc = _stage1(yf, xf, yn, xn)
        shimmer = _norm01(acc)
        cry_x = xn * cw
        cry_y = yn * ch
        cry = np.sin(cry_x * 0.502 + cry_y * 0.731 + si * 0.0015) * np.cos(
            cry_x * -0.389 + cry_y * 0.644 + si * 0.0021)
        hinge = np.sin(xn * 47.0 + yn * 31.0 + si * 0.08) * np.cos(xn * 31.0 - yn * 43.0 + si * 0.06)
        dm = (shimmer * 40.0 + np.abs(b3) * 26.0 + cry * 18.0 + hinge * 12.0) * eff
        dr = (-shimmer * 50.0 - np.abs(b1) * 22.0 - cry * 22.0 - hinge * 10.0) * eff
        dcc = ((shimmer - 0.5) * 2.0 * 24.0 + cry * 20.0 + np.abs(hinge) * 16.0 + b2 * 14.0) * eff
        return dm.astype(np.float32), dr.astype(np.float32), dcc.astype(np.float32)

    # Banded: stage1 to get the global shimmer normalisation constants, then full assemble banded.
    b1, b2, b3, acc = _stage1(yf, xf, yn, xn)
    a_mn = float(acc.min())
    a_mx = float(acc.max())
    # Match _norm01 exactly (divide, not reciprocal-multiply) so banding is bit-identical.
    a_denom = (a_mx - a_mn) + 1e-8
    a_flat = a_mx <= a_mn

    def _stage2(yn, xn, b1, b2, b3, acc):
        if a_flat:
            shimmer = np.zeros_like(acc, dtype=np.float32)
        else:
            shimmer = ((acc - a_mn) / a_denom).astype(np.float32)
        cry_x = xn * cw
        cry_y = yn * ch
        cry = np.sin(cry_x * 0.502 + cry_y * 0.731 + si * 0.0015) * np.cos(
            cry_x * -0.389 + cry_y * 0.644 + si * 0.0021)
        hinge = np.sin(xn * 47.0 + yn * 31.0 + si * 0.08) * np.cos(xn * 31.0 - yn * 43.0 + si * 0.06)
        dm = (shimmer * 40.0 + np.abs(b3) * 26.0 + cry * 18.0 + hinge * 12.0) * eff
        dr = (-shimmer * 50.0 - np.abs(b1) * 22.0 - cry * 22.0 - hinge * 10.0) * eff
        dcc = ((shimmer - 0.5) * 2.0 * 24.0 + cry * 20.0 + np.abs(hinge) * 16.0 + b2 * 14.0) * eff
        return dm.astype(np.float32), dr.astype(np.float32), dcc.astype(np.float32)

    return _band_channels(shape_work, (yn, xn, b1, b2, b3, acc), _stage2)


def living_motion_overlay(shape, seed, sm, m, r, cc, weight=1.0):
    """Static-map trick for *living* BRDF: layered anisotropic beats misaligned across M / R / Cc.

    iRacing-style materials cannot animate; this stacks competing phase fields at different
    orientations and scales so specular islands **crawl** when the eye, car, or sun moves.
    Resolution-aware frequencies keep 2K/4K previews from exploding into mud.
    """
    if weight <= 0:
        return m, r, cc
    h, w = shape
    ref_full = float(max(h, w))
    m = np.asarray(m, dtype=np.float32)
    r = np.asarray(r, dtype=np.float32)
    cc = np.asarray(cc, dtype=np.float32)
    if ref_full >= float(_LIVING_HALF_OVERLAY_MIN):
        scale = min(0.5, float(_LIVING_BRDF_WORK_CAP) / ref_full)
        hs = max(96, int(round(h * scale)))
        ws = max(96, int(round(w * scale)))
        dm, dr, dcc = _living_motion_deltas((hs, ws), seed, weight, ref_full)
        dm = _resize_array(dm, h, w)
        dr = _resize_array(dr, h, w)
        dcc = _resize_array(dcc, h, w)
    else:
        dm, dr, dcc = _living_motion_deltas(shape, seed, weight, ref_full)
    m = m + dm * float(sm)
    r = r + dr * float(sm)
    cc = cc + dcc * float(sm)
    return m, r, cc


def _living_paint_edge_shimmer(effect, mask, gain=0.062):
    """Boost perceived motion: micro-contrast on effect luminance (diffuse carries spec read)."""
    mask_hw = _mask2(mask, effect.shape[:2])
    lum = (
        effect[:, :, 0] * 0.2126
        + effect[:, :, 1] * 0.7152
        + effect[:, :, 2] * 0.0722
    )
    edge = _edge_energy(lum, 18.0)
    return np.clip(effect + edge[:, :, np.newaxis] * gain * mask_hw[:, :, np.newaxis], 0.0, 1.0)


def _living_triplet_micro_detail(shape, seed, driver, edge_f, m, r, cc, sm, strength=1.0):
    """Asset-free channel decorrelation: stacked beats misaligned across M/R/Cc (VM-style richness).

    `driver` should be a 0..1 field (e.g. discharge, caustic) so detail hugs motifs, not flat noise.
    """
    if strength <= 0:
        return m, r, cc
    h, w = shape
    ref_full = float(max(h, w))
    driver_a = np.asarray(driver, dtype=np.float32)
    edge_a = np.asarray(edge_f, dtype=np.float32)
    m = np.asarray(m, dtype=np.float32)
    r = np.asarray(r, dtype=np.float32)
    cc = np.asarray(cc, dtype=np.float32)

    if ref_full >= float(_LIVING_HALF_TRIPLET_MIN):
        scale = min(0.5, float(_LIVING_BRDF_WORK_CAP) / ref_full)
        hs = max(96, int(round(h * scale)))
        ws = max(96, int(round(w * scale)))
        d_s = _resize_array(driver_a, hs, ws)
        e_s = _resize_array(edge_a, hs, ws)
        work_shape = (hs, ws)
        driver_w, edge_w = d_s, e_s
    else:
        work_shape = shape
        driver_w, edge_w = driver_a, edge_a

    yf, xf, yn, xn = _coords(work_shape)
    si = int(seed) % 10007
    p = np.clip(driver_w, 0.0, 1.0) * 6.28318
    e = np.clip(edge_w, 0.0, 1.0) * 5.5
    f1 = np.sin(xf * 0.51 + yf * 0.37 + p * 9.0 + si * 0.013)
    f2 = np.cos(xf * -0.44 + yf * 0.48 + e * 11.0 + si * 0.019)
    f3 = np.sin((xn + yn) * 92.0 + si * 0.06) * np.cos((xn - yn) * 77.0 + p * 3.0)
    f4 = np.sin(xf * 0.119 - yf * 0.086 + np.sin(p * 2.0) * 1.7)
    mix = _norm01(f1 * 0.30 + f2 * 0.28 + f3 * 0.26 + f4 * 0.16)
    warm = np.clip(driver_w - edge_w * 0.35, 0.0, 1.0)
    eff = float(strength)
    dm = (mix * 32.0 + warm * np.abs(f3) * 22.0 + np.abs(f4) * 14.0) * eff
    dr = (-mix * 42.0 - warm * np.abs(f1) * 18.0 - np.abs(f2) * 12.0) * eff
    dcc = ((mix - 0.5) * 2.0 * 26.0 + warm * f2 * 19.0 + np.abs(f3) * 14.0) * eff

    if ref_full >= float(_LIVING_HALF_TRIPLET_MIN):
        dm = _resize_array(dm.astype(np.float32), h, w)
        dr = _resize_array(dr.astype(np.float32), h, w)
        dcc = _resize_array(dcc.astype(np.float32), h, w)

    m = m + dm * float(sm)
    r = r + dr * float(sm)
    cc = cc + dcc * float(sm)
    return m, r, cc


def _fast_field_from(field_fn, shape, seed, cap=None, detail_seed=0, detail_angle=0.0):
    h, w = shape
    if cap is None:
        cap = _LIVING_FIELD_FAST_CAP
    if max(h, w) <= cap:
        return None
    key = (field_fn.__name__, (int(h), int(w)), int(seed))
    cached = _FIELD_CACHE.get(key)
    if cached is not None:
        return cached.copy()
    scale = float(cap) / float(max(h, w))
    small_shape = (max(96, int(round(h * scale))), max(96, int(round(w * scale))))
    small = field_fn(small_shape, seed)
    up = _resize_array(np.asarray(small, dtype=np.float32), h, w)
    carrier = _micro_line_field(shape, seed + detail_seed, angle=detail_angle, freq=0.56)
    grain = _hash_noise(shape, seed + detail_seed + 37)
    out = _norm01(up * 0.90 + carrier * 0.075 + grain * 0.025)
    if len(_FIELD_CACHE) > 18:
        _FIELD_CACHE.clear()
    _FIELD_CACHE[key] = out.copy()
    return out


def _spec_prism(shape, seed, field, edge, sm, phase=0.0, power=1.0):
    micro = _micro_line_field(shape, seed, angle=phase * 6.28318, freq=0.36 + phase * 0.19)
    grain = _hash_noise(shape, seed + 31)
    hue = np.mod(field * 0.62 + edge * 0.28 + micro * 0.20 + grain * 0.055 + phase, 1.0)
    val = np.clip(0.25 + np.power(np.clip(field * 0.70 + edge * 0.95 + micro * 0.28, 0, 1), power), 0, 1)
    rgb = _hsv_to_rgb(hue, np.full(shape, 0.92, dtype=np.float32), val)
    return (
        18 + rgb[:, :, 0] * 225 * sm,
        18 + rgb[:, :, 1] * 225 * sm,
        18 + rgb[:, :, 2] * 225 * sm,
    )


def _living_spec_mix(shape, seed, field, edge, driver, sm, hue=0.0, sparkle=0.0):
    micro_a = _micro_line_field(shape, seed + 1, angle=0.23 + hue, freq=0.58)
    micro_b = _micro_line_field(shape, seed + 2, angle=-0.67 + hue * 0.7, freq=0.41)
    grain = _hash_noise(shape, seed + 3)
    field = np.asarray(field, dtype=np.float32)
    edge = np.asarray(edge, dtype=np.float32)
    driver = np.asarray(driver, dtype=np.float32)

    def _body(field, edge, driver, micro_a, micro_b, grain):
        chrome = np.clip(edge * 1.22 + driver * 0.72 + micro_a * 0.22, 0, 1)
        chrome = np.clip((chrome - 0.46) * 2.15, 0, 1)
        colored_metal = np.clip(np.sin(field * 13.0 + micro_b * 5.2 + hue * 6.28318) * 0.5 + 0.5, 0, 1)
        glass = np.clip(np.sin(driver * 9.0 - field * 7.0 + micro_a * 3.0) * 0.5 + 0.5, 0, 1)
        rough = np.clip(np.sin(field * -11.0 + micro_b * 4.4 + 2.1) * 0.5 + 0.5, 0, 1)
        spark = (grain > (0.965 - sparkle * 0.055)).astype(np.float32) * np.clip(chrome + edge, 0, 1)
        m = 8 + (chrome * 225 + colored_metal * 168 * (1 - chrome * 0.35) + spark * 230) * sm
        r = 14 + (rough * 218 * (1 - chrome * 0.78) + colored_metal * 58 - chrome * 54 + spark * 8) * sm
        cc = 10 + (glass * 150 + chrome * 228 + spark * 235) * sm
        return m, r, cc

    return _band_channels(shape, (field, edge, driver, micro_a, micro_b, grain), _body)


@lru_cache(maxsize=32)
def _body_flow_core(shape, seed):
    h, w = shape
    yf, xf, yn, xn = _coords(shape)
    center = 0.50 + 0.10 * np.sin(xn * 6.0 + seed * 0.041) + 0.035 * np.sin(xn * 17.0)
    shoulder = np.exp(-((yn - (center - 0.18)) ** 2) / 0.0038)
    belt = np.exp(-((yn - center) ** 2) / 0.0085)
    rocker = np.exp(-((yn - (center + 0.22)) ** 2) / 0.0060)
    nose_sweep = np.exp(-((xn - 0.17) ** 2) / 0.026) * np.exp(-((yn - 0.43) ** 2) / 0.16)
    deck_sweep = np.exp(-((xn - 0.77) ** 2) / 0.045) * np.exp(-((yn - 0.53) ** 2) / 0.12)
    panel_gain = np.clip(shoulder * 0.55 + belt * 0.85 + rocker * 0.45 + nose_sweep * 0.42 + deck_sweep * 0.34, 0, 1)
    seam = np.maximum(
        np.exp(-((yn - (0.27 + 0.04 * np.sin(xn * 12.0))) ** 2) / 0.00065),
        np.exp(-((yn - (0.73 + 0.03 * np.sin(xn * 10.0 + 0.7))) ** 2) / 0.00080),
    )
    sweep = xf * (0.030 + panel_gain * 0.016) + yf * (0.010 + belt * 0.030)
    sweep += np.sin((xf + yf) * 0.006 + seed * 0.13) * 1.4
    return sweep.astype(np.float32), panel_gain.astype(np.float32), seam.astype(np.float32), belt.astype(np.float32)


@lru_cache(maxsize=32)
def _body_flow(shape, seed):
    h, w = shape
    ref_full = float(max(h, w))
    if ref_full <= float(_LIVING_BRDF_WORK_CAP):
        return _body_flow_core(shape, seed)
    scale = float(_LIVING_BRDF_WORK_CAP) / ref_full
    work_shape = (max(96, int(round(h * scale))), max(96, int(round(w * scale))))
    flow, panel_gain, seam, belt = _body_flow_core(work_shape, seed)
    return (
        _resize_array(flow, h, w).astype(np.float32, copy=False),
        _resize_array(panel_gain, h, w).astype(np.float32, copy=False),
        _resize_array(seam, h, w).astype(np.float32, copy=False),
        _resize_array(belt, h, w).astype(np.float32, copy=False),
    )


@lru_cache(maxsize=24)
def _field_wave_tide_core(shape, seed):
    h, w = shape
    yf, xf, _, _ = _coords(shape)
    flow, panel_gain, seam, belt = _body_flow(shape, seed)
    warp_y = (np.sin(xf * 0.019 + seed * 0.13) + np.sin((xf + yf) * 0.011)) * h * 0.010
    warp_x = (np.sin(yf * 0.023 + seed * 0.09) + np.sin((xf - yf) * 0.014)) * w * 0.008
    y = yf + warp_y
    x = xf + warp_x
    body_swell = np.sin(flow + panel_gain * 3.2 - np.sin(y * 0.012) * 0.45)
    counter = np.sin(flow * -0.72 + x * 0.061 + y * 0.019 + seam * 1.8)
    capillary = np.sin(flow * 3.35 + y * 0.145 + body_swell * 1.10)
    shear = np.sin(flow * -2.10 + x * 0.114 + counter * 1.20)
    wake = np.clip(np.sin((body_swell + counter) * 3.4 + capillary * 1.7), 0, 1)
    glitter = _hash_noise(shape, seed + 14) * 0.16
    staged = panel_gain * (body_swell * 0.28 + wake * 0.20) + seam * 0.10
    return _norm01(staged + capillary * 0.24 + shear * 0.24 + counter * 0.10 + glitter * 0.04)


@lru_cache(maxsize=24)
def _field_wave_tide(shape, seed):
    fast = _fast_field_from(_field_wave_tide_core, shape, seed, detail_seed=14, detail_angle=0.46)
    if fast is not None:
        return fast
    return _field_wave_tide_core(shape, seed)


def spec_living_wave_tide(shape, mask, seed, sm):
    wave = _field_wave_tide(shape, seed)
    edge = _edge_energy(wave, 20.0)
    flow, panel_gain, seam, _belt = _body_flow(shape, seed)
    prism = _micro_line_field(shape, seed + 40, angle=0.46, freq=0.68)

    def _body(wave, edge, flow, panel_gain, seam, prism):
        traveling = np.clip(np.sin(flow * 1.55 + wave * 5.8) * 0.5 + 0.5, 0, 1)
        pulse = np.clip(edge * 1.25 + traveling * panel_gain * 0.92 + seam * 0.60, 0, 1)
        chrome_flash = np.clip((pulse - 0.48) * 2.15 + prism * edge * 0.85, 0, 1)
        rough_green = np.clip((1.0 - traveling) * panel_gain * 1.05 + (1.0 - prism) * 0.28, 0, 1)
        clear_blue = np.clip(traveling * prism * 1.20 + seam * 0.70 + edge * 0.42, 0, 1)
        red_orange = np.clip(np.sin(wave * 16.0 + flow * 0.62) * 0.5 + 0.5, 0, 1)
        purple_flip = np.clip(np.sin(wave * -13.0 + prism * 4.0 + 1.8) * 0.5 + 0.5, 0, 1)
        m = 8 + np.clip(chrome_flash * 1.05 + red_orange * panel_gain * 0.72 + edge * 0.28, 0, 1) * 238 * sm
        r = 10 + np.clip(rough_green * 0.95 + red_orange * 0.54 - chrome_flash * 0.66, 0, 1) * 230 * sm
        cc = 8 + np.clip(clear_blue * 1.08 + purple_flip * panel_gain * 0.78 + chrome_flash * 0.52, 0, 1) * 240 * sm
        return m, r, cc

    m, r, cc = _band_channels(shape, (wave, edge, flow, panel_gain, seam, prism), _body)
    m, r, cc = living_motion_overlay(shape, seed, sm, m, r, cc, weight=1.22)
    return _spec_out(shape, mask, m, r, cc)


def paint_living_wave_tide(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    mask = _mask2(mask, shape)
    wave = _field_wave_tide(shape, seed)
    edge = _edge_energy(wave, 15.0)
    _flow, panel_gain, seam, belt = _body_flow(shape, seed)
    micro_edge = _micro_line_field(shape, seed + 19, angle=0.46, freq=0.64)
    bb3 = _bb3(bb, shape)

    def _body(paint, wave, edge, panel_gain, seam, belt, micro_edge, bb3):
        crest = np.clip((wave - 0.45) * 2.4, 0, 1)
        trough = np.clip((0.42 - wave) * 2.8, 0, 1)
        stage = np.clip(panel_gain * 0.74 + seam * 0.32 + belt * 0.18, 0, 1)
        effect = paint.copy() * (0.30 + stage[:, :, None] * 0.18)
        effect[:, :, 0] += (crest * 0.025 + edge * 0.030 + micro_edge * 0.018) * (0.35 + stage)
        effect[:, :, 1] += (crest * 0.11 + edge * 0.12 + micro_edge * 0.08) * (0.45 + stage)
        effect[:, :, 2] += (trough * 0.22 + edge * 0.19 + micro_edge * 0.15) * (0.55 + stage * 0.80)
        effect = np.clip(effect + bb3 * 0.35 * crest[:, :, None], 0, 1)
        return effect

    effect = _band_image(shape, (paint, wave, edge, panel_gain, seam, belt, micro_edge, bb3), _body)
    return _finish_paint(paint, _living_paint_edge_shimmer(effect, mask), mask, pm)


@lru_cache(maxsize=24)
def _field_lake_ripple_core(shape, seed):
    h, w = shape
    yf, xf, _, _ = _coords(shape)
    flow, panel_gain, seam, belt = _body_flow(shape, seed + 4)
    rng = np.random.RandomState(seed + 120)
    field = np.zeros(shape, dtype=np.float32)
    caustic = np.zeros(shape, dtype=np.float32)
    for i in range(4):
        cx = (0.12 + i * 0.22 + rng.uniform(-0.025, 0.035)) * w
        cy = (0.36 + 0.24 * np.sin(i * 1.37 + seed * 0.17) + rng.uniform(-0.055, 0.055)) * h
        dist = np.sqrt((yf - cy) ** 2 + (xf - cx) ** 2)
        period = rng.uniform(max(5.0, min(h, w) / 180.0), max(18.0, min(h, w) / 70.0))
        phase = rng.uniform(0, np.pi * 2)
        decay = np.exp(-dist / rng.uniform(min(h, w) * 0.22, min(h, w) * 0.55))
        ring = np.sin(dist / period * np.pi * 2 + phase)
        panel_weight = 0.58 + panel_gain * 0.95 + seam * 0.34
        field += ring * decay * rng.uniform(0.42, 0.82) * panel_weight
        caustic += np.exp(-np.abs(ring) * 13.5) * decay * (0.24 + panel_gain * 0.36)
    wind = _micro_line_field(shape, seed + 126, angle=0.20, freq=0.58)
    crosswind = _micro_line_field(shape, seed + 127, angle=-0.12, freq=0.33)
    current = np.sin(flow * 1.28 + wind * 2.4)
    traveling = np.clip(np.sin(flow * 2.05 + field * 1.7) * 0.5 + 0.5, 0, 1)
    return _norm01(field * 0.42 + caustic * 0.46 + wind * 0.16 + crosswind * 0.10 + current * 0.13 + traveling * belt * 0.20)


@lru_cache(maxsize=24)
def _field_lake_ripple(shape, seed):
    fast = _fast_field_from(_field_lake_ripple_core, shape, seed, detail_seed=127, detail_angle=0.20)
    if fast is not None:
        return fast
    return _field_lake_ripple_core(shape, seed)


def spec_living_lake_ripple(shape, mask, seed, sm):
    rip = _field_lake_ripple(shape, seed)
    edge = _edge_energy(rip, 18.0)
    flow, panel_gain, seam, belt = _body_flow(shape, seed + 4)
    yf, xf, _, _ = _coords(shape)
    micro_a = _micro_line_field(shape, seed + 131, angle=0.18, freq=0.82)
    micro_b = _micro_line_field(shape, seed + 132, angle=-0.34, freq=0.61)
    # Seam-sensitive: glint's _norm01 spans the whole array — precompute on full arrays.
    caustic_full = np.clip((rip - 0.54) * 3.4, 0, 1)
    lace_full = np.clip(edge * 1.55 + np.abs(micro_a - micro_b) * caustic_full * 1.35, 0, 1)
    glint_raw = np.sin(xf * 0.58 + yf * 0.44 + rip * 24.0 + seed * 0.02) * np.cos(
        xf * -0.49 + yf * 0.52 + edge * 9.0 + caustic_full * 14.0
    )
    glint = _norm01(np.abs(glint_raw)) * np.clip(caustic_full * 1.12 + lace_full * 0.42 + seam * 0.22, 0, 1)

    def _body(rip, edge, flow, panel_gain, seam, belt, micro_a, micro_b, glint):
        caustic = np.clip((rip - 0.54) * 3.4, 0, 1)
        lace = np.clip(edge * 1.55 + np.abs(micro_a - micro_b) * caustic * 1.35, 0, 1)
        travel_a = np.sin(flow * 1.55 + rip * 11.0)
        travel_b = np.sin(flow * 2.15 - rip * 8.0 + 1.9)
        travel_c = np.sin(flow * -1.70 + edge * 5.5 + 3.1)
        panel_pulse = np.clip(panel_gain * (travel_a * 0.5 + 0.5) + seam * 0.72 + belt * caustic * 0.62, 0, 1)
        blue_clear = np.clip((travel_c * 0.5 + 0.5) * np.maximum(panel_pulse, caustic) * 1.28 + lace * 0.72, 0, 1)
        green_rough = np.clip((travel_b * 0.5 + 0.5) * panel_pulse * 1.05 + (1.0 - caustic) * edge * 0.36, 0, 1)
        cyan_metal = np.clip((travel_a * 0.5 + 0.5) * caustic * 1.20 + lace * 0.78, 0, 1)
        chrome_caustic = np.clip(edge * 1.24 + caustic * panel_pulse * 1.38 + lace * 0.74, 0, 1)
        dark_trough = np.clip(1.0 - np.maximum(panel_pulse, lace) * 1.45, 0, 1)
        m = 7 + np.clip(cyan_metal * 0.44 + chrome_caustic * 0.46 + lace * 0.12, 0, 1) * 208 * sm
        r = 12 + np.clip(green_rough * 1.18 + edge * 0.36 + lace * 0.38 - chrome_caustic * 0.30 + dark_trough * 0.28, 0, 1) * 236 * sm
        cc = 8 + np.clip(blue_clear * 1.15 + chrome_caustic * 0.72 + seam * 0.30, 0, 1) * 242 * sm
        m = m.astype(np.float32) + glint * (46.0 * sm)
        r = r.astype(np.float32) - glint * (38.0 * sm)
        cc = cc.astype(np.float32) + glint * (32.0 * sm)
        return m, r, cc

    m, r, cc = _band_channels(
        shape, (rip, edge, flow, panel_gain, seam, belt, micro_a, micro_b, glint), _body
    )
    m, r, cc = _living_triplet_micro_detail(shape, seed + 811, rip, edge, m, r, cc, sm, strength=0.62)
    m, r, cc = living_motion_overlay(shape, seed, sm, m, r, cc, weight=1.20)
    return _spec_out(shape, mask, m, r, cc)


def paint_living_lake_ripple(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    mask = _mask2(mask, shape)
    rip = _field_lake_ripple(shape, seed)
    edge = _edge_energy(rip, 18.0)
    yf, xf, _, _ = _coords(shape)
    _flow, panel_gain, seam, belt = _body_flow(shape, seed + 4)
    bb3 = _bb3(bb, shape)

    def _body(paint, rip, edge, yf, xf, panel_gain, seam, belt, bb3):
        caustic = np.clip(edge * 1.4 + np.clip((rip - 0.62) * 2.6, 0, 1), 0, 1)
        glint_paint = np.clip(
            np.sin(xf * 0.55 + yf * 0.42 + rip * 22.0 + seed * 0.015) ** 2 * (caustic + edge * 0.35),
            0,
            1,
        )
        stage = np.clip(panel_gain * 0.55 + seam * 0.20 + belt * 0.20, 0, 1)
        effect = paint.copy() * (0.62 + rip[:, :, None] * 0.10 + stage[:, :, None] * 0.12)
        effect[:, :, 0] += caustic * (0.020 + stage * 0.035) + glint_paint * (0.045 + stage * 0.04)
        effect[:, :, 1] += caustic * (0.18 + stage * 0.18) + glint_paint * (0.11 + stage * 0.10)
        effect[:, :, 2] += caustic * (0.30 + stage * 0.22) + glint_paint * (0.14 + stage * 0.12)
        effect = np.clip(effect + bb3 * 0.28 * caustic[:, :, None], 0, 1)
        return effect

    effect = _band_image(shape, (paint, rip, edge, yf, xf, panel_gain, seam, belt, bb3), _body)
    return _finish_paint(paint, _living_paint_edge_shimmer(effect, mask), mask, pm)


@lru_cache(maxsize=24)
def _field_flame_flicker_core(shape, seed):
    h, w = shape
    yf, xf, yn, xn = _coords(shape)
    warp = np.sin(xf * 0.043 + yf * 0.019 + seed * 0.1) * 0.055
    xwarp = xn + warp + np.sin(yn * 42.0 + seed * 0.03) * 0.018
    lick_a = np.sin(xwarp * 112.0 + yn * 26.0 + np.sin(yf * 0.045) * 1.6)
    lick_b = np.sin(xwarp * 74.0 - yn * 83.0 + np.sin(xf * 0.038) * 1.9)
    lick_c = _micro_line_field(shape, seed + 211, angle=-0.92, freq=0.48)
    tongues = _norm01(lick_a * 0.46 + lick_b * 0.34 + lick_c * 0.28)
    vertical_heat = np.clip(1.16 - yn * 0.95, 0.0, 1.0) ** 0.62
    cells = _hash_noise(shape, seed + 212)
    ember = np.clip(np.sin(xf * 0.31 + yf * 0.19 + cells * 3.5), 0, 1) ** 3.0
    licking_edges = np.clip((tongues - 0.36) * 3.3, 0, 1)
    return np.clip(licking_edges * vertical_heat + ember * 0.22, 0, 1).astype(np.float32)


@lru_cache(maxsize=24)
def _field_flame_flicker(shape, seed):
    fast = _fast_field_from(_field_flame_flicker_core, shape, seed, detail_seed=219, detail_angle=-0.92)
    if fast is not None:
        return fast
    return _field_flame_flicker_core(shape, seed)


def spec_living_flame_flicker(shape, mask, seed, sm):
    flame = _field_flame_flicker(shape, seed)
    edge = _edge_energy(flame, 20.0)
    filament_a = _micro_line_field(shape, seed + 247, angle=-0.94, freq=0.86)
    filament_b = _micro_line_field(shape, seed + 248, angle=-1.18, freq=0.53)
    ember = _hash_noise(shape, seed + 244)

    def _body(flame, edge, filament_a, filament_b, ember):
        hair = np.clip(np.abs(filament_a - filament_b) * 1.55 + edge * 1.15, 0, 1)
        hot = np.clip((flame - 0.31) * 2.36 + edge * 0.54 + hair * flame * 0.42, 0, 1)
        white_hot = np.clip((hot - 0.78) * 4.8 + hair * 0.38, 0, 1)
        purple_edge = np.clip(edge * 1.45 * (1 - white_hot * 0.35) + (1 - flame) * hair * 0.22, 0, 1)
        char = np.clip((0.52 - flame) * 2.6, 0, 1)
        ember_pin = (ember > 0.982).astype(np.float32) * np.clip(hair + hot, 0, 1)
        m = 6 + np.clip(hot * 1.10 + char * 0.34 + edge * 0.42 + ember_pin * 0.95, 0, 1) * 242 * sm
        r = 8 + np.clip(hot * 0.90 + char * 0.62 + purple_edge * 0.20 - white_hot * 0.58, 0, 1) * 226 * sm
        cc = 7 + np.clip(white_hot * 1.16 + purple_edge * 0.62 + hair * hot * 0.40 + ember_pin * 0.72, 0, 1) * 242 * sm
        return m, r, cc

    m, r, cc = _band_channels(shape, (flame, edge, filament_a, filament_b, ember), _body)
    m, r, cc = living_motion_overlay(shape, seed, sm, m, r, cc, weight=1.18)
    return _spec_out(shape, mask, m, r, cc)


def paint_living_flame_flicker(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    mask = _mask2(mask, shape)
    flame = _field_flame_flicker(shape, seed)
    edge = _edge_energy(flame, 18.0)

    def _body(paint, flame, edge):
        core = np.clip((flame - 0.34) * 2.15, 0, 1)
        white_hot = np.clip((core - 0.84) * 3.6 + edge * 0.26, 0, 1)
        # Push palette toward amber / gold / yellow-orange (less “sports orange + black”).
        hue = 0.052 + (1 - core) * 0.095 - white_hot * 0.028 + edge * 0.014
        sat = np.clip(0.92 + core * 0.06 - white_hot * 0.58, 0, 1)
        val = np.clip(0.02 + core * 1.22 + edge * 0.40 + white_hot * 0.62, 0, 1)
        fire = _hsv_to_rgb(hue, sat, val)
        red_glow = np.zeros_like(fire)
        red_glow[:, :, 0] = np.clip(core * 1.28 + edge * 0.48, 0, 1)
        red_glow[:, :, 1] = np.clip(core * 0.42 + edge * 0.38, 0, 1)
        red_glow[:, :, 2] = np.clip(edge * 0.08 + core * 0.05, 0, 1)
        char = paint * (0.018 + core[:, :, None] * 0.10)
        return np.clip(char + fire * (0.18 + core[:, :, None] * 1.12) + red_glow * 0.40, 0, 1)

    effect = _band_image(shape, (paint, flame, edge), _body)
    return _finish_paint(paint, _living_paint_edge_shimmer(effect, mask), mask, pm)


@lru_cache(maxsize=24)
def _field_led_chase(shape, seed):
    h, w = shape
    yf, xf, yn, xn = _coords(shape)
    cell = max(3.1, min(h, w) / 150.0)
    gx = np.floor(xf / cell)
    gy = np.floor(yf / cell)
    lx = (xf / cell) - gx - 0.5
    ly = (yf / cell) - gy - 0.5
    radius = np.sqrt(lx * lx + ly * ly)
    diode = np.clip(1.0 - radius / 0.285, 0, 1) ** 2.18
    micro_lens = np.clip(1.0 - radius / 0.150, 0, 1) ** 3.6
    phase = np.mod(gx * 0.137 + gy * 0.233 + np.sin((gx - gy) * 0.37 + seed * 0.05) * 0.21, 1.0)
    chase_a = np.exp(-((phase - 0.205) ** 2) / 0.0038)
    chase_b = np.exp(-((phase - 0.610) ** 2) / 0.0046) * 0.92
    chase_c = np.exp(-((phase - 0.855) ** 2) / 0.0029) * 0.64
    cell_hash = np.sin(gx * 19.19 + gy * 73.73 + seed * 0.37) * 43758.5453
    cell_hash = cell_hash - np.floor(cell_hash)
    ghost = (np.sin(gx * 1.7 + gy * 2.3 + seed) * 0.5 + 0.5) ** 3.0 * 0.18
    sleeper = ((cell_hash > 0.82).astype(np.float32) * 0.12 + 0.018)
    return np.clip(diode * (chase_a + chase_b + chase_c + ghost + sleeper) + micro_lens * (chase_a + chase_b) * 0.28, 0, 1).astype(np.float32)


def _resize_spec_to_shape(spec_small, shape, mask):
    h, w = shape
    out = np.zeros((h, w, 4), dtype=np.uint8)
    for channel in range(3):
        out[:, :, channel] = np.clip(
            _resize_array(spec_small[:, :, channel].astype(np.float32), h, w),
            0,
            255,
        ).astype(np.uint8)
    out[:, :, 3] = np.clip(_mask2(mask, shape) * 255, 0, 255).astype(np.uint8)
    return out


def _spec_living_led_chase_native(shape, mask, seed, sm):
    led = _field_led_chase(shape, seed)
    yf, xf, _, _ = _coords(shape)
    cell = max(3.1, min(shape) / 150.0)
    gx = np.floor(xf / cell)
    gy = np.floor(yf / cell)
    lx = (xf / cell) - gx - 0.5
    ly = (yf / cell) - gy - 0.5
    radius = np.sqrt(lx * lx + ly * ly)
    cell_hash = np.sin(gx * 19.19 + gy * 73.73 + seed * 0.37) * 43758.5453
    cell_hash = cell_hash - np.floor(cell_hash)
    angle = cell_hash * np.pi * 2.0
    ca = np.cos(angle)
    sa = np.sin(angle)
    axial = lx * ca + ly * sa
    lateral = -lx * sa + ly * ca
    inner = np.clip(1.0 - radius / 0.128, 0, 1) ** 3.15
    glass = np.clip(1.0 - radius / 0.245, 0, 1) ** 2.05
    rim = np.exp(-((radius - 0.222) ** 2) / 0.00070)
    crescent = np.exp(-((axial - (cell_hash - 0.5) * 0.070) ** 2) / 0.0017) * np.exp(-(lateral ** 2) / 0.018)
    ruby_sliver = np.exp(-((axial + 0.082) ** 2) / 0.00042) * np.exp(-(lateral ** 2) / 0.0065)
    amber_sliver = np.exp(-((axial - 0.074) ** 2) / 0.00072) * np.exp(-(lateral ** 2) / 0.0100)
    local_a = np.sin((lx * ca + ly * sa) * 215.0 + gy * 0.91 + seed * 0.07)
    local_b = np.sin((-lx * sa + ly * ca) * 188.0 + gx * 0.83 + seed * 0.11)
    diode_micro = np.clip(local_a * local_b * 0.5 + 0.5, 0, 1)
    hot_gate = (diode_micro > (0.885 + cell_hash * 0.070)).astype(np.float32)
    lit = np.clip((led - 0.205) * 4.25, 0, 1)
    half_lit = np.clip((led - 0.065) * 2.10, 0, 1) * (1 - lit * 0.78)
    red_body = np.clip(glass * (lit * 0.54 + half_lit * 0.18), 0, 1)
    red_core = np.clip(inner * lit * (0.78 + diode_micro * 0.44), 0, 1)
    orange_facets = np.clip((amber_sliver * 0.82 + crescent * 0.34 + rim * 0.26) * (lit + half_lit * 0.45), 0, 1)
    ruby_facets = np.clip((ruby_sliver * 0.86 + inner * hot_gate * diode_micro * 1.18) * lit, 0, 1)
    pin = np.clip(inner * hot_gate * lit * (0.88 + diode_micro * 0.95), 0, 1)
    dim_phosphor = np.clip(glass * half_lit * (0.25 + diode_micro * 0.26), 0, 1)
    dot_body = np.clip(red_body + red_core + orange_facets + ruby_facets + dim_phosphor, 0, 1)
    m = (red_body * 118 + red_core * 242 + orange_facets * 224 + ruby_facets * 252 + pin * 255 + dim_phosphor * 42) * sm
    r_dot = 210 - red_body * 126 - red_core * 184 - orange_facets * 128 - ruby_facets * 190 - pin * 202 + dim_phosphor * 24
    cc_dot = 235 - red_body * 112 - red_core * 182 - orange_facets * 166 - ruby_facets * 190 - pin * 218 + rim * lit * 28
    r = np.where(dot_body > 0.030, r_dot, 250 + _hash_noise(shape, seed + 333) * 5)
    cc = np.where(dot_body > 0.030, cc_dot, 250 + _hash_noise(shape, seed + 334) * 5)
    # Per-diode twinkle: brightness breathes on lit pixels (reads as LEDs catching angle changes).
    tw = (np.sin(float(seed) * 0.31 + gx * 2.07 + gy * 2.71) * 0.5 + 0.5) ** 2.1
    tw_amp = (0.78 + tw * 0.38).astype(np.float32)
    dot_mask = (dot_body > 0.055).astype(np.float32)
    m = np.asarray(m, dtype=np.float32) * (1.0 + dot_mask * (tw_amp - 1.0))
    cc = np.asarray(cc, dtype=np.float32) + dot_mask * tw * (26.0 * sm)
    r = np.asarray(r, dtype=np.float32) - dot_mask * tw * (14.0 * sm)
    m, r, cc = living_motion_overlay(shape, seed, sm, m, r, cc, weight=0.88)
    return _spec_out(shape, mask, m, r, cc)


def spec_living_led_chase(shape, mask, seed, sm):
    h, w = shape
    if max(h, w) > _LIVING_LED_WORK_CAP:
        scale = float(_LIVING_LED_WORK_CAP) / float(max(h, w))
        work_shape = (max(96, int(round(h * scale))), max(96, int(round(w * scale))))
        mask_small = _resize_array(_mask2(mask, shape), work_shape[0], work_shape[1])
        spec_small = _spec_living_led_chase_native(work_shape, mask_small, seed, sm)
        return _resize_spec_to_shape(spec_small, shape, mask)
    return _spec_living_led_chase_native(shape, mask, seed, sm)


def _paint_living_led_chase_effect(paint, shape, seed):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    led = _field_led_chase(shape, seed)
    yf, xf, _, _ = _coords(shape)
    cell = max(3.1, min(shape) / 150.0)
    gx = np.floor(xf / cell)
    gy = np.floor(yf / cell)
    lx = (xf / cell) - gx - 0.5
    ly = (yf / cell) - gy - 0.5
    radius = np.sqrt(lx * lx + ly * ly)
    cell_hash = np.sin(gx * 23.11 + gy * 41.07 + seed * 0.31) * 43758.5453
    cell_hash = cell_hash - np.floor(cell_hash)
    local = np.clip(np.sin(lx * 192.0 + seed * 0.13) * np.sin(ly * 177.0 + gy * 0.21) * 0.5 + 0.5, 0, 1)
    lit = np.clip((led - 0.205) * 3.65, 0, 1)
    ghost = np.clip((led - 0.045) * 1.65, 0, 1) * (1 - lit * 0.70)
    diode_shape = np.clip(1.0 - radius / 0.255, 0, 1) ** 2.1
    lens = np.clip(1.0 - radius / 0.112, 0, 1) ** 2.8
    hue = np.mod(0.002 + cell_hash * 0.074 + local * 0.018, 1.0)
    value = np.clip(diode_shape * (ghost * 0.72 + lit * 1.68) + lens * lit * (0.85 + local * 0.62), 0, 1)
    saturation = np.clip(0.90 + local * 0.10, 0, 1)
    diode_color = _hsv_to_rgb(hue, saturation, value)
    hot_pin = lens * lit * (local > 0.91).astype(np.float32)
    red_white = np.stack([
        np.ones(shape, dtype=np.float32),
        np.full(shape, 0.28, dtype=np.float32) + local * 0.28,
        np.full(shape, 0.08, dtype=np.float32) + local * 0.18,
    ], axis=-1)
    dark_board = paint * np.array([0.026, 0.018, 0.016], dtype=np.float32)
    effect = np.clip(dark_board + diode_color * (0.42 + lit[:, :, None] * 1.90 + ghost[:, :, None] * 0.66) + red_white * hot_pin[:, :, None] * 0.62, 0, 1)
    return effect


def paint_living_led_chase(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    mask = _mask2(mask, shape)
    h, w = shape
    if max(h, w) > _LIVING_LED_WORK_CAP:
        scale = float(_LIVING_LED_WORK_CAP) / float(max(h, w))
        work_shape = (max(96, int(round(h * scale))), max(96, int(round(w * scale))))
        paint_small = _resize_array(paint, work_shape[0], work_shape[1])
        effect_small = _paint_living_led_chase_effect(paint_small, work_shape, seed)
        effect = np.clip(_resize_array(effect_small, h, w), 0, 1)
    else:
        effect = _paint_living_led_chase_effect(paint, shape, seed)
    return _finish_paint(paint, _living_paint_edge_shimmer(effect, mask), mask, pm)


@lru_cache(maxsize=24)
def _field_twinkle_stars(shape, seed):
    h, w = shape
    yf, xf, _, _ = _coords(shape)
    cell = max(4.2, min(h, w) / 104.0)
    gx = np.floor(xf / cell)
    gy = np.floor(yf / cell)
    lx = (xf / cell) - gx - 0.5
    ly = (yf / cell) - gy - 0.5
    rnd = np.sin(gx * 37.17 + gy * 91.43 + seed * 0.61) * 43758.5453
    rnd = rnd - np.floor(rnd)
    active = (rnd > 0.57).astype(np.float32)
    pin = np.exp(-(lx * lx + ly * ly) / 0.0085)
    cross = np.exp(-(np.abs(lx) + np.abs(ly)) / 0.095) * 0.26
    twinkle = (np.sin(gx * 1.31 + gy * 2.17 + seed) * 0.5 + 0.5) ** 1.35
    return np.clip(active * (pin + cross) * (0.35 + twinkle), 0, 1).astype(np.float32)


def spec_living_twinkle_stars(shape, mask, seed, sm):
    stars = _field_twinkle_stars(shape, seed)
    edge = _edge_energy(stars, 13.0)
    yf, xf, _, _ = _coords(shape)
    bg_noise = _hash_noise(shape, seed + 382)
    cell = max(4.2, min(shape) / 104.0)
    block_cell = max(7.0, cell * 1.8)

    def _body(stars, edge, yf, xf, bg_noise):
        gx = np.floor(xf / cell)
        gy = np.floor(yf / cell)
        lx = (xf / cell) - gx - 0.5
        ly = (yf / cell) - gy - 0.5
        radius2 = lx * lx + ly * ly
        rnd = np.sin(gx * 11.13 + gy * 53.71 + seed * 0.29) * 43758.5453
        blue = ((rnd - np.floor(rnd)) > 0.50).astype(np.float32)
        block = np.mod(np.floor(xf / block_cell) + np.floor(yf / block_cell), 2.0)
        bg = (bg_noise > 0.55).astype(np.float32) * (0.12 + block * 0.060)
        pin = np.exp(-radius2 / 0.0036)
        flare = np.exp(-(np.abs(lx) + np.abs(ly)) / 0.060)
        halo = np.exp(-radius2 / 0.020)
        micro = np.clip(np.sin(lx * 168.0 + gy) * np.sin(ly * 151.0 + gx) * 0.5 + 0.5, 0, 1)
        star_hash = np.sin(gx * 41.13 + gy * 17.71 + seed * 0.53) * 43758.5453
        star_hash = star_hash - np.floor(star_hash)
        snap_gate = (micro > (0.60 + star_hash * 0.22)).astype(np.float32)
        twinkle = np.clip(stars * 1.72 + edge * 1.22 + pin * stars * micro * 1.55, 0, 1)
        snap = np.clip((pin * stars * snap_gate * (0.85 + micro) + edge * stars * 0.82), 0, 1)
        wink_shadow = np.clip(halo * stars * (1 - snap) * (1 - micro) * 0.38, 0, 1)
        yellow_m = 238 * twinkle + snap * 36
        yellow_r = 206 * twinkle + flare * stars * 58 - snap * 72
        yellow_cc = 28 * twinkle + snap * 210 + wink_shadow * 18
        blue_m = 36 * twinkle + snap * 142
        blue_r = 50 * twinkle + wink_shadow * 56
        blue_cc = 238 * twinkle + snap * 36
        m = 8 + (bg * 48 + ((1 - blue) * yellow_m + blue * blue_m)) * sm
        r = 12 + (bg * 62 + ((1 - blue) * yellow_r + blue * blue_r)) * sm
        cc = 10 + (bg * 44 + ((1 - blue) * yellow_cc + blue * blue_cc)) * sm
        return m, r, cc

    m, r, cc = _band_channels(shape, (stars, edge, yf, xf, bg_noise), _body)
    m, r, cc = living_motion_overlay(shape, seed, sm, m, r, cc, weight=1.30)
    return _spec_out(shape, mask, m, r, cc)


def paint_living_twinkle_stars(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    mask = _mask2(mask, shape)
    stars = _field_twinkle_stars(shape, seed)
    yf, xf, _, _ = _coords(shape)
    dust = _hash_noise(shape, seed + 371)
    cell = max(4.2, min(shape) / 104.0)
    block_cell = max(7.0, cell * 1.8)

    def _body(paint, stars, yf, xf, dust):
        gx = np.floor(xf / cell)
        gy = np.floor(yf / cell)
        rnd = np.sin(gx * 11.13 + gy * 53.71 + seed * 0.29) * 43758.5453
        blue = ((rnd - np.floor(rnd)) > 0.50).astype(np.float32)[:, :, None]
        yellow_color = np.array([1.00, 0.78, 0.12], dtype=np.float32)
        blue_color = np.array([0.12, 0.42, 1.00], dtype=np.float32)
        star_color = ((1 - blue) * yellow_color + blue * blue_color) * np.clip(stars[:, :, None] * 1.95, 0, 1)
        block = np.mod(np.floor(xf / block_cell) + np.floor(yf / block_cell), 2.0)[:, :, None]
        dust_color = ((1 - blue) * yellow_color + blue * blue_color) * np.clip((dust[:, :, None] - 0.50) * 0.12, 0, 0.050)
        base = paint * np.array([0.025, 0.030, 0.052], dtype=np.float32) + block * np.array([0.010, 0.011, 0.016], dtype=np.float32)
        return np.clip(base + dust_color + star_color * (0.28 + stars[:, :, None] * 1.25), 0, 1)

    effect = _band_image(shape, (paint, stars, yf, xf, dust), _body)
    return _finish_paint(paint, _living_paint_edge_shimmer(effect, mask), mask, pm)


@lru_cache(maxsize=24)
def _field_neon_equalizer_core(shape, seed):
    h, w = shape
    yf, xf, yn, xn = _coords(shape)
    cell = max(5.0, min(h, w) / 118.0)
    gx = np.floor(xf / cell)
    gy = np.floor(yf / cell)
    lx = (xf / cell) - gx - 0.5
    ly = (yf / cell) - gy - 0.5
    lane = np.sin((gx + gy * 0.42) * 0.34 + seed * 0.08)
    cluster = np.sin((gx - gy * 0.72) * 0.21 + np.sin((gx + gy) * 0.061) * 2.0)
    active = ((lane + cluster) > 0.48).astype(np.float32)
    capsule = np.exp(-(lx * lx) / 0.018) * np.exp(-(ly * ly) / 0.070)
    ticks = (np.sin(gy * 2.9 + gx * 0.7 + seed) * 0.5 + 0.5) ** 3.2
    diagonal = _micro_line_field(shape, seed + 439, angle=0.68, freq=0.38)
    burst = np.clip(np.sin(xf * 0.060 + yf * 0.044 + diagonal * 4.0) * 0.5 + 0.5, 0, 1) ** 2.4
    return np.clip(active * capsule * (0.35 + ticks * 0.80) + burst * diagonal * 0.38, 0, 1).astype(np.float32)


@lru_cache(maxsize=24)
def _field_neon_equalizer(shape, seed):
    fast = _fast_field_from(_field_neon_equalizer_core, shape, seed, detail_seed=439, detail_angle=0.74)
    if fast is not None:
        return fast
    return _field_neon_equalizer_core(shape, seed)


def spec_living_neon_equalizer(shape, mask, seed, sm):
    eq = _field_neon_equalizer(shape, seed)
    edge = _edge_energy(eq, 16.0)
    micro = _micro_line_field(shape, seed + 445, angle=0.74, freq=0.80)
    yf, xf, yn, xn = _coords(shape)
    # Seam-sensitive prep: driver/strobe/phase_c feed scan_w, whose _norm01 spans the whole
    # array (a per-band min/max would differ) — compute scan_w on full arrays before banding.
    driver = np.clip(eq * 1.28 + edge * 0.96 + micro * eq * 0.24, 0, 1)
    strobe = np.clip(np.sin(eq * 28.0 + edge * 6.0 + micro * 5.5) * 0.5 + 0.5, 0, 1)
    phase_c = np.sin(eq * 18.0 - driver * 3.0 + 4.0)
    scan = np.sin(xf * 0.074 + eq * 29.0 + seed * 0.048) * np.cos(yn * 52.0 + phase_c * 1.8)
    scan_w = _norm01(np.abs(scan)) * np.clip(driver * 0.85 + strobe * 0.45, 0, 1)

    def _body(eq, edge, micro, driver, strobe, scan_w):
        phase_b = np.sin(eq * -12.0 + edge * 5.0 + 2.2)
        lit = np.clip((eq - 0.13) * 3.25 + edge * 0.62, 0, 1)
        chrome = np.clip((driver - 0.44) * 2.15 + edge * 0.72 + lit * strobe * 0.74, 0, 1)
        mirror_sliver = np.clip(chrome * (0.38 + micro * 1.05) * (0.55 + strobe * 0.70), 0, 1)
        hue = np.mod(0.75 - eq * 0.82 + micro * 0.22 + edge * 0.11, 1.0)
        bleed_rgb = _hsv_to_rgb(hue, np.full(eq.shape, 0.96, dtype=np.float32), np.clip(lit * 0.90 + strobe * driver * 0.42, 0, 1))
        color_bleed = np.clip(lit * (0.32 + strobe * 0.54) + edge * 0.26, 0, 1)
        m = 6 + np.clip(lit * 0.72 + bleed_rgb[:, :, 0] * color_bleed * 0.72 + mirror_sliver * 0.96, 0, 1) * 248 * sm
        r = 7 + np.clip(bleed_rgb[:, :, 1] * color_bleed * 0.86 + (phase_b * 0.5 + 0.5) * lit * 0.28 + edge * 0.20 - mirror_sliver * 0.62, 0, 1) * 224 * sm
        cc = 6 + np.clip(bleed_rgb[:, :, 2] * color_bleed * 0.88 + lit * 0.58 + mirror_sliver * 1.06, 0, 1) * 250 * sm
        m = m + scan_w * (46.0 * sm)
        r = r - scan_w * (38.0 * sm)
        cc = cc + scan_w * (34.0 * sm)
        return m.astype(np.float32), r.astype(np.float32), cc.astype(np.float32)

    m, r, cc = _band_channels(shape, (eq, edge, micro, driver, strobe, scan_w), _body)
    m, r, cc = _living_triplet_micro_detail(shape, seed + 901, eq, edge, m, r, cc, sm, strength=0.88)
    m, r, cc = living_motion_overlay(shape, seed, sm, m, r, cc, weight=1.22)
    return _spec_out(shape, mask, m, r, cc)


def paint_living_neon_equalizer(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    mask = _mask2(mask, shape)
    eq = _field_neon_equalizer(shape, seed)
    _, xf, _, xn = _coords(shape)
    # bloom needs an _edge_energy (np.diff, seam-sensitive) — compute on full arrays first.
    bloom = np.clip(eq + _edge_energy(eq, 13.0) * 0.42, 0, 1)

    def _body(paint, eq, xf, xn, bloom):
        neon = _hsv_to_rgb(np.mod(0.78 - xn * 0.58 + eq * 0.12, 1.0), np.full(eq.shape, 0.94), np.clip(eq * 1.35, 0, 1))
        base = paint * np.array([0.08, 0.07, 0.14], dtype=np.float32)
        scan_bloom = np.clip(np.sin(xf * 0.088 + eq * 26.0 + seed * 0.05) ** 2, 0, 1)
        lift = bloom[:, :, None] * 1.18 + scan_bloom[:, :, None] * 0.42
        return np.clip(base + neon * (0.58 + lift), 0, 1)

    effect = _band_image(shape, (paint, eq, xf, xn, bloom), _body)
    return _finish_paint(paint, _living_paint_edge_shimmer(effect, mask), mask, pm)


@lru_cache(maxsize=24)
def _field_heat_haze_core(shape, seed):
    h, w = shape
    yf, xf, yn, xn = _coords(shape)
    shear_a = _micro_line_field(shape, seed + 510, angle=1.48, freq=0.34)
    shear_b = _micro_line_field(shape, seed + 511, angle=1.25, freq=0.57)
    flame_edge = np.sin(yf * 0.071 + np.sin(xf * 0.032 + seed) * 2.4)
    shimmer = np.sin((xf + shear_a * w * 0.018) * 0.066 + yn * 13.0)
    vertical = np.clip(1.05 - yn * 0.72, 0.14, 1.0)
    pockets = np.clip(np.sin(flame_edge * 2.2 + shimmer * 1.3), 0, 1)
    return _norm01((shear_a * 0.32 + shear_b * 0.28 + pockets * 0.36 + shimmer * 0.10) * vertical)


@lru_cache(maxsize=24)
def _field_heat_haze(shape, seed):
    fast = _fast_field_from(_field_heat_haze_core, shape, seed, detail_seed=519, detail_angle=1.35)
    if fast is not None:
        return fast
    return _field_heat_haze_core(shape, seed)


def spec_living_heat_haze(shape, mask, seed, sm):
    hz_detail = 1.28
    haze = _field_heat_haze(shape, seed)
    edge = _edge_energy(haze, 18.0)
    micro_a = _micro_line_field(shape, seed + 524, angle=1.42, freq=0.73)
    micro_b = _micro_line_field(shape, seed + 525, angle=1.10, freq=0.49)
    grit = _hash_noise(shape, seed + 527)

    def _body(haze, edge, micro_a, micro_b, grit):
        grit_w = np.clip(np.abs(grit - 0.5) * 2.4, 0, 1) * edge * 0.42
        lace = np.clip(np.abs(micro_a - micro_b) * (1.42 * hz_detail) + edge * (1.18 * hz_detail) + grit_w * 0.55, 0, 1)
        burn = np.clip(edge * (1.92 * hz_detail) + np.clip((haze - 0.55) * (2.95 * hz_detail), 0, 1) + lace * haze * 0.52, 0, 1)
        shimmer = np.clip(np.sin(haze * 18.0 + edge * 5.7 + micro_a * 2.2) * 0.5 + 0.5, 0, 1)
        cool_void = np.clip(1.0 - burn * 1.35 - lace * 0.28, 0, 1)
        hot_ridge = np.clip((burn - 0.36) * 2.35 + edge * 0.38, 0, 1)
        thin_edge = np.clip((lace - 0.34) * 2.20, 0, 1)
        inner_outline = np.exp(-((haze - 0.40) ** 2) / 0.0018) * thin_edge
        outer_outline = np.exp(-((haze - 0.68) ** 2) / 0.0024) * np.clip(edge * 1.45 + thin_edge * 0.40, 0, 1)
        red_outline = np.clip(inner_outline * 0.90 + outer_outline * 1.15 + edge * burn * 0.42, 0, 1)
        red_hot = np.clip(red_outline * (0.80 + (1 - shimmer) * 0.54) + hot_ridge * (1 - shimmer) * 0.34, 0, 1)
        orange_skin = np.clip(hot_ridge * shimmer * (0.58 + micro_b * 0.48), 0, 1)
        pink_flash = np.clip(hot_ridge * thin_edge * (0.22 + micro_a * 0.70) + edge * shimmer * 0.18, 0, 1)
        violet_cool = np.clip(cool_void * thin_edge * (0.22 + micro_b * 0.92), 0, 1)
        blue_knife = np.clip(cool_void * edge * 1.15 + np.clip(micro_a - 0.66, 0, 1) * (1 - burn) * 1.7, 0, 1)
        soot = np.clip(1.0 - red_hot * 1.25 - orange_skin * 1.10 - pink_flash * 0.90 - blue_knife * 0.70, 0, 1)
        chrome_red = np.clip(red_outline * (0.72 + thin_edge * 0.62), 0, 1)
        m = 5 + np.clip(chrome_red * 1.26 + red_outline * 0.52 + orange_skin * 0.62 + pink_flash * 0.42 + violet_cool * 0.10 + soot * 0.025, 0, 1) * 250 * sm
        r = 7 + np.clip(orange_skin * 0.96 + red_hot * 0.05 + shimmer * thin_edge * 0.14 + violet_cool * 0.20 - chrome_red * 0.88 - pink_flash * 0.28 + soot * 0.04, 0, 1) * 238 * sm
        cc = 5 + np.clip(chrome_red * 0.10 + pink_flash * 0.56 + blue_knife * 0.88 + violet_cool * 0.74 + orange_skin * 0.06, 0, 1) * 242 * sm
        return m, r, cc

    m, r, cc = _band_channels(shape, (haze, edge, micro_a, micro_b, grit), _body)
    m, r, cc = living_motion_overlay(shape, seed, sm, m, r, cc, weight=1.24)
    return _spec_out(shape, mask, m, r, cc)


def paint_living_heat_haze(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    mask = _mask2(mask, shape)
    haze = _field_heat_haze(shape, seed)
    edge = _edge_energy(haze, 18.0)
    lace = _micro_line_field(shape, seed + 526, angle=1.37, freq=0.70)

    def _body(paint, haze, edge, lace):
        warm = np.array([1.0, 0.40, 0.04], dtype=np.float32)
        yellow = np.array([1.0, 0.82, 0.16], dtype=np.float32)
        red = np.array([0.90, 0.08, 0.02], dtype=np.float32)
        flame_tint = warm * (1 - haze[:, :, None]) + yellow * haze[:, :, None]
        flame_tint = flame_tint * (1 - edge[:, :, None] * 0.50) + red * edge[:, :, None] * 0.50
        hot = np.clip(edge * 0.85 + haze * 0.48 + lace * edge * 0.40, 0, 1)
        return np.clip(paint * (0.46 + edge[:, :, None] * 0.12) + flame_tint * (0.18 + hot[:, :, None] * 0.62), 0, 1)

    effect = _band_image(shape, (paint, haze, edge, lace), _body)
    return _finish_paint(paint, _living_paint_edge_shimmer(effect, mask), mask, pm)


def _field_electric_current_impl(shape, seed):
    """Bolt + spark field at native `shape` (keep small — caller may downsample work buffer)."""
    h, w = shape
    yf, xf, yn, xn = _coords(shape)
    rng = np.random.RandomState(seed + 620)
    spark_noise = _hash_noise(shape, seed + 660)
    field = np.zeros(shape, dtype=np.float32)
    n_bolts = 6
    for i in range(n_bolts):
        y0 = rng.uniform(0.12, 0.88)
        slope = rng.uniform(-0.55, 0.55)
        amp = rng.uniform(0.010, 0.044)
        freq = rng.uniform(18.0, 52.0)
        center = y0 + slope * (xn - 0.5) + amp * np.sin(xn * freq + rng.uniform(0, np.pi * 2))
        center += np.sin(xn * freq * 2.7 + yn * 4.8 + i) * 0.0035
        dist = np.abs(yn - center)
        core = np.exp(-(dist ** 2) / rng.uniform(0.0000015, 0.000006))
        halo = np.exp(-(dist ** 2) / rng.uniform(0.000035, 0.000130)) * 0.13
        branch_offset = 0.010 + 0.010 * np.sin(xn * rng.uniform(30, 64) + i)
        branch = np.exp(-((dist - branch_offset) ** 2) / 0.000008) * 0.12
        thr = 0.991 + float(i) * 0.00055 + rng.uniform(-0.0015, 0.0015)
        sparks = (spark_noise > thr).astype(np.float32) * np.exp(-(dist ** 2) / 0.00028) * 0.58
        field += core + halo + branch + sparks
    return np.clip(field, 0, 1).astype(np.float32)


@lru_cache(maxsize=24)
def _field_electric_current(shape, seed):
    """Always simulate arcs on a capped buffer, then upscale — fast path for any preview ≥ ~640px."""
    h, w = shape
    mx = max(h, w)
    cap_w = _LIVING_ELECTRIC_WORK_CAP
    if mx > cap_w:
        sc = cap_w / float(mx)
        sh = max(96, int(round(h * sc)))
        sw = max(96, int(round(w * sc)))
        fld = _field_electric_current_impl((sh, sw), seed)
        return np.clip(_resize_array(fld, h, w), 0.0, 1.0).astype(np.float32)
    return _field_electric_current_impl(shape, seed)


def spec_living_electric_current(shape, mask, seed, sm):
    current = _field_electric_current(shape, seed)
    edge = _edge_energy(current, 18.0)
    filament = _micro_line_field(shape, seed + 651, angle=0.03, freq=0.74)
    grain = _hash_noise(shape, seed + 652)

    def _body(current, edge, filament, grain):
        hot = np.clip(current * 1.28 + edge * 0.92, 0, 1)
        sparkle = (grain > 0.983).astype(np.float32) * np.clip(hot + edge * 0.65, 0, 1)
        m = 10 + np.clip(current * 1.15 + edge * 0.82 + filament * hot * 0.55 + sparkle * 0.42, 0, 1) * 236 * sm
        r = 12 + np.clip(edge * 0.35 + current * 0.16 - hot * 0.30 - sparkle * 0.22, 0, 1) * 118 * sm
        cc = 14 + np.clip(edge * 1.20 + hot * 0.82 + filament * current * 0.42 + sparkle * 0.38, 0, 1) * 238 * sm
        return m, r, cc

    m, r, cc = _band_channels(shape, (current, edge, filament, grain), _body)
    m, r, cc = _living_triplet_micro_detail(shape, seed + 701, current, edge, m, r, cc, sm, strength=1.42)
    m, r, cc = living_motion_overlay(shape, seed, sm, m, r, cc, weight=1.32)
    return _spec_out(shape, mask, m, r, cc)


def paint_living_electric_current(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    mask = _mask2(mask, shape)
    current = _field_electric_current(shape, seed)
    edge = _edge_energy(current, 18.0)
    yf, xf, _, _ = _coords(shape)

    def _body(paint, current, edge, yf, xf):
        arcHue = np.sin(current * 38.0 + edge * 11.0 + seed * 0.02) * 0.5 + 0.5
        electric = np.zeros_like(paint, dtype=np.float32)
        electric[:, :, 0] = current * (0.42 + arcHue * 0.18) + edge * 0.58
        electric[:, :, 1] = current * (0.68 + arcHue * 0.14) + edge * 0.62
        electric[:, :, 2] = current * (1.18 + (1.0 - arcHue) * 0.16) + edge * 0.98
        zap = np.clip(np.sin(xf * 0.38 + yf * 0.29 + current * 55.0) ** 2 * edge * current, 0, 1)
        electric[:, :, 0] += zap * 0.22
        electric[:, :, 1] += zap * 0.35
        electric[:, :, 2] += zap * 0.52
        base = paint * np.array([0.07, 0.08, 0.15], dtype=np.float32)
        return np.clip(base + electric * 1.15, 0, 1)

    effect = _band_image(shape, (paint, current, edge, yf, xf), _body)
    return _finish_paint(paint, _living_paint_edge_shimmer(effect, mask), mask, pm)


@lru_cache(maxsize=24)
def _field_oil_pulse_core(shape, seed):
    h, w = shape
    yf, xf, yn, xn = _coords(shape)
    slick = np.sin(xn * 8.0 + np.sin(yn * 11.0 + seed) * 1.6)
    sheet_a = np.sin(xf * 0.030 + yf * 0.016 + slick * 2.2)
    sheet_b = np.sin(xf * -0.024 + yf * 0.038 + np.sin(xn * 5.2) * 1.8)
    sheet_c = np.sin((xf + yf) * 0.020 + sheet_a * 2.4 - sheet_b * 1.7)
    fine = np.sin(xf * 0.116 - yf * 0.071 + sheet_c * 2.0)
    film = _micro_line_field(shape, seed + 721, angle=-0.22, freq=0.18)
    return _norm01(sheet_a * 0.24 + sheet_b * 0.24 + sheet_c * 0.20 + fine * 0.18 + film * 0.14)


@lru_cache(maxsize=24)
def _field_oil_pulse(shape, seed):
    fast = _fast_field_from(_field_oil_pulse_core, shape, seed, detail_seed=729, detail_angle=-0.22)
    if fast is not None:
        return fast
    return _field_oil_pulse_core(shape, seed)


def spec_living_oil_pulse(shape, mask, seed, sm):
    oil = _field_oil_pulse(shape, seed)
    edge = _edge_energy(oil, 16.0)
    driver = np.clip(np.sin(oil * 17.0 + edge * 4.0) * 0.5 + 0.5, 0, 1)
    m, r, cc = _living_spec_mix(shape, seed + 750, oil, edge, driver, sm, hue=0.64, sparkle=0.22)

    def _body(oil, edge, m, r, cc):
        thin_a = np.sin(oil * 24.0 + edge * 5.0)
        thin_b = np.sin(oil * 29.0 - edge * 4.2 + 2.0)
        thin_c = np.sin(oil * 34.0 + edge * 3.4 + 4.1)
        m = np.maximum(m, 12 + np.clip((thin_a * 0.5 + 0.5) * 0.88 + edge * 0.46, 0, 1) * 224 * sm)
        r = np.clip(r + np.clip((thin_b * 0.5 + 0.5) * 0.74 + (1 - oil) * 0.30, 0, 1) * 142 * sm - edge * 92 * sm, 8, 245)
        cc = np.maximum(cc, 10 + np.clip((thin_c * 0.5 + 0.5) * 0.90 + edge * 0.66, 0, 1) * 236 * sm)
        return m, r, cc

    m, r, cc = _band_channels(shape, (oil, edge, m, r, cc), _body)
    m, r, cc = living_motion_overlay(shape, seed, sm, m, r, cc, weight=1.20)
    return _spec_out(shape, mask, m, r, cc)


def paint_living_oil_pulse(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    mask = _mask2(mask, shape)
    oil = _field_oil_pulse(shape, seed)
    edge = _edge_energy(oil, 16.0)

    def _body(paint, oil, edge):
        hue = np.mod(0.56 + oil * 1.18 + edge * 0.28, 1.0)
        film = _hsv_to_rgb(hue, np.full(oil.shape, 0.92), np.clip(0.12 + oil * 0.78 + edge * 0.68, 0, 1))
        base = paint * (0.10 + oil[:, :, None] * 0.10)
        return np.clip(base + film * (0.28 + edge[:, :, None] * 0.74), 0, 1)

    effect = _band_image(shape, (paint, oil, edge), _body)
    return _finish_paint(paint, _living_paint_edge_shimmer(effect, mask), mask, pm)


LIVING_FINISH_REGISTRY = {
    "living_wave_tide": (spec_living_wave_tide, paint_living_wave_tide),
    "living_lake_ripple": (spec_living_lake_ripple, paint_living_lake_ripple),
    "living_flame_flicker": (spec_living_flame_flicker, paint_living_flame_flicker),
    "living_led_chase": (spec_living_led_chase, paint_living_led_chase),
    "living_twinkle_stars": (spec_living_twinkle_stars, paint_living_twinkle_stars),
    "living_neon_equalizer": (spec_living_neon_equalizer, paint_living_neon_equalizer),
    "living_heat_haze": (spec_living_heat_haze, paint_living_heat_haze),
    "living_electric_current": (spec_living_electric_current, paint_living_electric_current),
    "living_oil_pulse": (spec_living_oil_pulse, paint_living_oil_pulse),
}


LIVING_FINISH_GROUPS = {
    "SHOKKER Living Finishes": list(LIVING_FINISH_REGISTRY.keys()),
}


def integrate_living_finishes(engine_module):
    if not hasattr(engine_module, "MONOLITHIC_REGISTRY"):
        engine_module.MONOLITHIC_REGISTRY = {}
    engine_module.MONOLITHIC_REGISTRY.update(LIVING_FINISH_REGISTRY)
    reg = engine_module.MONOLITHIC_REGISTRY
    sorted_reg = dict(sorted(reg.items()))
    reg.clear()
    reg.update(sorted_reg)
    print(f"[Living Finishes] Loaded {len(LIVING_FINISH_REGISTRY)} SHOKKER Living finishes")
    return {"living_finishes": len(LIVING_FINISH_REGISTRY)}
