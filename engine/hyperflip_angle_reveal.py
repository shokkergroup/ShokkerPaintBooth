"""COLORSHOXX HyperFlip — Electric-Storm-style angle-reveal family.

SPB owner 2026-05-27 — each HyperFlip gets its own paint + spec identity.
Buried palette + fine 8–32px gates + directional flash (see docs/COLORSHOXX_ANGLE_REVEAL.md).
Hue/sat/brightness sliders exist in the booth — color-only clones are pointless.

SPB owner 2026-05-27 tick-2 — spec MUST trace paint geometry per finish.
Never route HyperFlips through a universal _cx_angle_reveal_spec / shared pin template.
"""

from __future__ import annotations

from collections import OrderedDict

import cv2
import numpy as np

from engine.paint_v2.structural_color import (
    _cx_buried_reveal_gate,
    _cx_directional_mask,
    _cx_fine_spec_pins,
    _cx_hash01,
    _cx_ultra_micro,
    _cx_xy,
)


def _shape_hw(shape):
    return shape[:2] if len(shape) > 2 else shape


def _paint3(paint):
    if paint.ndim == 3 and paint.shape[2] > 3:
        return paint[:, :, :3].copy()
    return paint


def _pack_spec(M, R, CC, mask, shape):
    h, w = _shape_hw(shape)
    # 2026-06-20 COLORSHOXX HyperFlip rework: _hf_marry_spec drove M/R/Cc from one
    # `flash` field (|corr|~1.0). Add fake-3D bevel relief + decorrelate R/Cc via the
    # shared depth3d post-pass (deterministic per-finish seed from the M content).
    try:
        from engine.paint_v2 import depth3d_2026 as _d3
        _M = np.asarray(M, np.float32)
        _seed = int(abs(float(_M.mean()) * 131.0) + abs(float(_M[::97, ::97].sum()))) & 0x7FFFFFFF
        M, R, CC = _d3.decorrelate_envelope(_M, R, CC, seed=_seed, blend=0.66)
    except Exception:
        pass
    m = mask.astype(np.float32, copy=False)
    spec = np.empty((h, w, 4), dtype=np.uint8)
    keep = m > 0.01
    spec[:, :, 0] = np.clip(M * m, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.where(keep, np.clip(R, 15, 255), 0).astype(np.uint8)
    spec[:, :, 2] = np.where(keep, np.clip(CC, 16, 255), 0).astype(np.uint8)
    spec[:, :, 3] = np.clip(m * 255, 0, 255).astype(np.uint8)
    return spec


def _blend_paint(paint, color, mask, pm):
    bl = float(np.clip(float(pm) * 0.96, 0, 1))
    mb = (mask.astype(np.float32, copy=False) * bl)[:, :, np.newaxis]  # HxWx1 alpha
    ch3 = paint[:, :, :3]
    # ch3 = ch3*(1-mb) + color*mb  ==  ch3 + (color-ch3)*mb  (one temp, in-place)
    diff = color - ch3
    diff *= mb
    ch3 += diff
    np.clip(paint, 0, 1, out=paint)
    return paint.astype(np.float32, copy=False)


def _hf_add_accent(color, accent_rgb, scalar_hw):
    """color += accent_rgb * scalar_hw[...,None], clipped [0,1], in-place.

    Equivalent to the old `np.clip(color + accent3 * f1[...,None] * f2[...,None]
    * k * pm * msk, 0, 1)` chains but the per-pixel scalar weight is folded into a
    single HxW array by the caller, so only ONE HxWx3 broadcast-multiply temporary
    is built instead of four. Bit-identical (same float multiply order on scalars).
    """
    acc = np.asarray(accent_rgb, dtype=np.float32).reshape(1, 1, 3)
    color += acc * scalar_hw[:, :, np.newaxis]
    np.clip(color, 0, 1, out=color)
    return color


_HF_FIELD_CACHE = OrderedDict()
_HF_FIELD_CACHE_MAX = 48
_HF_WORK_MAX = 768


def _hf_work_shape(shape):
    h, w = _shape_hw(shape)
    work = min(_HF_WORK_MAX, int(h), int(w))
    if work >= min(h, w):
        return int(h), int(w)
    scale = float(work) / float(max(h, w))
    return max(128, int(round(h * scale))), max(128, int(round(w * scale)))


def _hf_resize(field, shape):
    h, w = _shape_hw(shape)
    if field.shape == (h, w):
        return field.astype(np.float32, copy=False)
    return cv2.resize(field.astype(np.float32, copy=False), (int(w), int(h)), interpolation=cv2.INTER_LINEAR).astype(np.float32)


def _hf_cached(key, factory):
    cached = _HF_FIELD_CACHE.get(key)
    if cached is not None:
        _HF_FIELD_CACHE.move_to_end(key)
        return cached
    out = factory()
    _HF_FIELD_CACHE[key] = out
    _HF_FIELD_CACHE.move_to_end(key)
    while len(_HF_FIELD_CACHE) > _HF_FIELD_CACHE_MAX:
        _HF_FIELD_CACHE.popitem(last=False)
    return out


# SPB perf loop 2026-06-13 (hyperflip lane): paint and spec for a finish both
# recompute the SAME full-res _cx_hash01 / _geo_* fields (same shape+seed) back
# to back. Memoize them (mirrors fractured_souls _FS_CACHE) so the spec pass —
# which runs immediately after paint with identical args — reuses the array.
# Returned arrays are treated read-only by callers (they always combine into a
# fresh array), so sharing is safe.
def _hf_hash01(shape, seed, salt=0):
    h, w = _shape_hw(shape)
    key = ("hash01", int(h), int(w), int(seed), int(salt))
    return _hf_cached(key, lambda: _cx_hash01((h, w), seed, salt))


# SPB perf loop 2026-06-13 (hyperflip lane): the carrier fields were already
# built at <=768 work-res then upscaled, so the cache now stores the WORK-RES
# field as the primitive. The full-res _hf_gate/_hf_micro/_hf_axis upscale on
# top (unchanged behavior — the spec path still gets full-res fields), while the
# paint path composes its color array at work-res via the *_w variants and
# upscales the finished color ONCE. resize(a)*resize(b) -> resize(a*b) is
# bilinearly equivalent for these smooth fields (validated SSIM>=0.997).
def _hf_gate_w(shape, seed, seed_off, density):
    h, w = _shape_hw(shape)
    work_shape = _hf_work_shape((h, w))
    key = ("gate_w", int(work_shape[0]), int(work_shape[1]), int(seed), int(seed_off), float(density))
    return _hf_cached(key, lambda: _cx_buried_reveal_gate(work_shape, seed, seed_off, density=density, layers=6))


def _hf_micro_w(shape, seed):
    h, w = _shape_hw(shape)
    work_shape = _hf_work_shape((h, w))
    key = ("micro_w", int(work_shape[0]), int(work_shape[1]), int(seed))
    return _hf_cached(key, lambda: _cx_ultra_micro(work_shape, seed))


def _hf_axis_w(shape, axis, seed):
    h, w = _shape_hw(shape)
    work_shape = _hf_work_shape((h, w))
    key = ("axis_w", int(work_shape[0]), int(work_shape[1]), str(axis), int(seed))
    return _hf_cached(key, lambda: _cx_directional_mask(work_shape, axis, seed))


def _hf_gate(shape, seed, seed_off, density):
    h, w = _shape_hw(shape)
    out = _hf_gate_w((h, w), seed, seed_off, density)
    return _hf_resize(out, (h, w)) if out.shape != (h, w) else out


def _hf_micro(shape, seed):
    h, w = _shape_hw(shape)
    out = _hf_micro_w((h, w), seed)
    return _hf_resize(out, (h, w)) if out.shape != (h, w) else out


def _hf_axis(shape, axis, seed):
    h, w = _shape_hw(shape)
    out = _hf_axis_w((h, w), axis, seed)
    return _hf_resize(out, (h, w)) if out.shape != (h, w) else out


def _hf_reveal_flash(shape, seed, seed_off, reveals, gate_density=0.0115):
    """Paint-matched buried reveal intensity — same gates/axes as _hf_paint_reveal."""
    h, w = _shape_hw(shape)
    gate = _hf_gate((h, w), seed, seed_off, gate_density)
    micro = _hf_micro((h, w), seed + seed_off * 17)
    flash = np.zeros((h, w), dtype=np.float32)
    for i, (_, axis, strength) in enumerate(reveals):
        axis_m = _hf_axis((h, w), axis, seed + seed_off + i * 419)
        layer = gate * axis_m
        layer *= float(strength)
        flash += layer
        np.clip(flash, 0, 1, out=flash)
    if reveals:
        flash /= len(reveals)
    mist = micro - 0.28
    mist *= 1.45
    np.clip(mist, 0, 1, out=mist)
    mist *= 0.22
    flash += mist
    np.clip(flash, 0, 1, out=flash)
    return flash.astype(np.float32, copy=False), gate, micro


def _hf_marry_spec(flash, sm, *, m_lo=8, m_hi=248, r_lo=198, r_hi=15, cc_lo=158, cc_hi=16,
                   pin=None, r_mod=None, cc_mod=None):
    """Paint-traced flash → M/R/CC. No _cx_fine_field / universal angle-reveal template."""
    flash = np.clip(flash, 0, 1)
    pins = np.clip(pin if pin is not None else flash, 0, 1)
    absorb = 1.0 - flash
    M = m_lo + flash * (m_hi - m_lo) * sm + pins * 58.0 * sm
    R = r_lo - flash * (r_lo - r_hi) * sm - pins * 48.0 * sm + absorb * 8.0
    CC = cc_lo - flash * (cc_lo - cc_hi) * sm * 0.92 + pins * 24.0 * sm
    if r_mod is not None:
        R = np.clip(R + r_mod * sm, 15, 255)
    if cc_mod is not None:
        CC = np.clip(CC + cc_mod * sm, 16, 255)
    return (
        np.clip(M, 0, 255).astype(np.float32),
        np.clip(R, 15, 255).astype(np.float32),
        np.clip(CC, 16, 255).astype(np.float32),
    )


def _hf_paint_reveal(paint, shape, mask, seed, pm, seed_off, body_rgb, shadow_rgb, reveals,
                     gate_density=0.0115, mist_colors=None, extra=None):
    """HyperFlip paint — booth-visible body + fine-gated opponent reveals.

    SPB perf loop 2026-06-13: bit-identical speedups only (validated SSIM==1.0,
    max-delta 0). The color composition stays at full 2048^2 (the mist/hash
    speckle carries real high-freq detail), but every stage now accumulates
    in-place to kill the dozens of 48 MB HxWx3 float temporaries the old
    `np.clip(color + a*b*c, 0, 1)` chains allocated, and the carrier/geo/hash
    fields are memoized so the spec pass (run right after paint, same seed) reuses
    them. ~3-4x faster end to end.
    """
    paint = _paint3(paint)
    h, w = _shape_hw(shape)
    body = np.asarray(body_rgb, dtype=np.float32).reshape(1, 1, 3)
    shadow = np.asarray(shadow_rgb, dtype=np.float32).reshape(1, 1, 3)
    base_col = np.clip(shadow * 0.42 + body * 0.58, 0, 1).reshape(3)
    color = np.empty((h, w, 3), dtype=np.float32)
    color[:] = base_col
    gate = _hf_gate((h, w), seed, seed_off, gate_density)
    micro = _hf_micro((h, w), seed + seed_off * 17)
    bl = np.clip(float(pm), 0, 1)
    for i, (rgb, axis, strength) in enumerate(reveals):
        axis_m = _hf_axis((h, w), axis, seed + seed_off + i * 419)
        rgb3 = np.asarray(rgb, dtype=np.float32).reshape(1, 1, 3)
        # layer (HxW) reused across the 3 broadcast channels; in-place accumulate
        layer = gate * axis_m
        layer *= (float(strength) * bl * 0.78)
        color += rgb3 * layer[:, :, np.newaxis]
        np.clip(color, 0, 1, out=color)
    if mist_colors:
        flakes = np.array(mist_colors, dtype=np.float32).reshape(-1, 3)
        sel = np.floor(_hf_hash01((h, w), seed, seed_off + 77) * len(flakes)).astype(np.int32)
        np.clip(sel, 0, len(flakes) - 1, out=sel)
        env = micro - 0.28
        env *= 1.45
        np.clip(env, 0, 1, out=env)
        env *= (0.26 * bl)
        color += flakes[sel] * env[:, :, np.newaxis]
        np.clip(color, 0, 1, out=color)
    sheen = (micro - 0.5).astype(np.float32)
    color += sheen[:, :, np.newaxis] * (body * (0.14 * bl))
    np.clip(color, 0, 1, out=color)
    if extra is not None:
        color = extra(color, (h, w), seed, pm, gate, mask)
    return _blend_paint(paint, color, mask, pm)


# ── Shared geometry (paint + spec must call the same field) ───────────────

def _geo_pink_slats(shape, seed):
    h, w = _shape_hw(shape)
    key = ("geo_slats", int(h), int(w), int(seed))
    def _make():
        x, _ = _cx_xy((h, w))
        slats = np.clip(0.5 + 0.5 * np.sin((x * 118.0 + seed * 0.003) * np.pi), 0, 1)
        return np.clip((slats - 0.68) * 5.5, 0, 1).astype(np.float32)
    return _hf_cached(key, _make)


def _geo_orange_rings(shape, seed):
    h, w = _shape_hw(shape)
    key = ("geo_rings", int(h), int(w), int(seed))
    def _make():
        x, y = _cx_xy((h, w))
        cx = 0.38 + 0.08 * np.sin(seed * 0.011)
        cy = 0.62 + 0.07 * np.cos(seed * 0.013)
        rings = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        pulse = np.clip(0.5 + 0.5 * np.sin(rings * 142.0 * np.pi + seed * 0.017), 0, 1)
        return np.clip((pulse - 0.48) * 3.2, 0, 1).astype(np.float32)
    return _hf_cached(key, _make)


def _hf_hex_gate(shape, seed, seed_off):
    h, w = _shape_hw(shape)
    key = ("hex", int(h), int(w), int(seed), int(seed_off))

    def _make():
        work_shape = _hf_work_shape((h, w))
        x, y = _cx_xy(work_shape)
        a = x * 1.15
        b = y * 0.92 + x * 0.38
        hx = np.clip(0.5 + 0.5 * np.cos(a * 58.0 * np.pi), 0, 1)
        hy = np.clip(0.5 + 0.5 * np.cos((a * 0.52 + b) * 58.0 * np.pi), 0, 1)
        hz = np.clip(0.5 + 0.5 * np.cos((b * 0.48 - a * 0.36) * 58.0 * np.pi), 0, 1)
        cell = np.clip((hx + hy + hz) / 3.0, 0, 1)
        edge = np.clip(1.0 - np.abs(cell - 0.52) * 9.0, 0, 1)
        pins = _cx_fine_spec_pins(work_shape, seed, seed_off, density=0.0066, layers=5)
        out = np.clip(edge * 0.68 + pins * 0.32, 0, 1).astype(np.float32)
        return _hf_resize(out, (h, w)) if work_shape != (h, w) else out

    return _hf_cached(key, _make)


def _geo_purple_rosette(shape, seed):
    h, w = _shape_hw(shape)
    key = ("geo_rosette", int(h), int(w), int(seed))
    def _make():
        h1 = _hf_hash01((h, w), seed, 91051)
        return np.clip((h1 - 0.88) * 12.0, 0, 1).astype(np.float32)
    return _hf_cached(key, _make)


def _geo_blue_copper_arcs(shape, seed):
    h, w = _shape_hw(shape)
    key = ("geo_arcs", int(h), int(w), int(seed))
    def _make():
        x, y = _cx_xy((h, w))
        arc = np.clip(0.5 + 0.5 * np.sin((x * 76.0 + np.cos(y * 94.0 + seed * 0.002) * 0.42) * np.pi), 0, 1)
        arc *= np.clip(0.5 + 0.5 * np.cos((y * 68.0 + arc * 0.6) * np.pi), 0, 1)
        return np.clip((arc - 0.50) * 4.2, 0, 1).astype(np.float32)
    return _hf_cached(key, _make)


def _geo_bronze_scan(shape, seed):
    h, w = _shape_hw(shape)
    key = ("bronze_scan", int(h), int(w), int(seed))

    def _make():
        work_shape = _hf_work_shape((h, w))
        _, y = _cx_xy(work_shape)
        scan = np.clip(0.5 + 0.5 * np.sin((y * 96.0 + seed * 0.005) * np.pi), 0, 1)
        out = np.clip((scan - 0.38) * 2.4, 0, 1).astype(np.float32)
        return _hf_resize(out, (h, w)) if work_shape != (h, w) else out

    return _hf_cached(key, _make)


def _geo_silver_frost(shape, seed):
    frost = _cx_ultra_micro(shape, seed + 91081)
    pearl = _hf_hash01(shape, seed, 91082)
    return np.clip((frost - 0.52) * 2.4 + (pearl - 0.68) * 2.8, 0, 1).astype(np.float32)


def _geo_midnight_opal_pins(shape, seed):
    opal_h = _hf_hash01(shape, seed, 91101)
    return np.clip((opal_h - 0.82) * 7.5, 0, 1).astype(np.float32)


# ── 9101 Red/Blue — classic dual-axis opponent reveal ─────────────────────

_REVEALS_9101 = [((0.95, 0.04, 0.03), "u", 0.92), ((0.04, 0.28, 0.98), "v", 0.88)]


def paint_hyperflip_red_blue(paint, shape, mask, seed, pm, bb):
    return _hf_paint_reveal(
        paint, shape, mask, seed, pm, 9101,
        (0.88, 0.06, 0.05), (0.06, 0.04, 0.05),
        _REVEALS_9101,
        mist_colors=[(0.04, 0.28, 0.98), (0.95, 0.04, 0.03)],
    )


def spec_hyperflip_red_blue(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    flash, gate, _ = _hf_reveal_flash(shape, seed, 9101, _REVEALS_9101)
    u = _hf_axis((h, w), "u", seed + 9101) * gate
    v = _hf_axis((h, w), "v", seed + 9201) * gate
    pins = _cx_fine_spec_pins((h, w), seed, 9101, density=0.0095, layers=6) * gate
    red_flash = np.clip(flash * 0.55 + u * 0.45, 0, 1)
    M, R, CC = _hf_marry_spec(red_flash, sm, pin=pins, r_mod=-u * 72.0 + v * 34.0)
    CC = np.clip(CC + v * 18.0 * sm - u * 6.0 * sm, 110, 255)
    return _pack_spec(M, R, CC, mask, shape)


# ── 9102 Pink/Black — vertical glass slat columns ─────────────────────────

_REVEALS_9102 = [((0.98, 0.08, 0.58), "v", 0.90), ((0.88, 0.04, 0.42), "u", 0.78)]


def paint_hyperflip_pink_black(paint, shape, mask, seed, pm, bb):
    def _slats(color, hw, sd, pm_, gate, msk):
        slats = _geo_pink_slats(hw, sd)
        w = (slats * gate) * (0.38 * pm_) * msk
        return _hf_add_accent(color, (0.98, 0.08, 0.58), w)

    return _hf_paint_reveal(
        paint, shape, mask, seed, pm, 9102,
        (0.92, 0.12, 0.52), (0.10, 0.06, 0.08),
        _REVEALS_9102,
        mist_colors=[(0.98, 0.08, 0.58), (0.88, 0.04, 0.42)],
        extra=lambda c, hw, sd, pm_, gate, msk: _slats(c, hw, sd, pm_, gate, msk),
    )


def spec_hyperflip_pink_black(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    slats = _geo_pink_slats((h, w), seed)
    flash, gate, _ = _hf_reveal_flash(shape, seed, 9102, _REVEALS_9102)
    chrome = slats * gate
    v = _hf_axis((h, w), "v", seed + 9102)
    flash = np.clip(chrome * v * 0.78 + flash * 0.22, 0, 1)
    pins = _cx_fine_spec_pins((h, w), seed, 9102, density=0.0078, layers=5) * chrome
    M, R, CC = _hf_marry_spec(flash, sm, m_hi=242, pin=pins, r_mod=-chrome * 38.0, cc_mod=-slats * 22.0)
    return _pack_spec(M, R, CC, mask, shape)


# ── 9103 Orange/Cyan — radial pulse rings on buried duo ───────────────────

_REVEALS_9103 = [((0.98, 0.42, 0.02), "diag_a", 0.88), ((0.02, 0.82, 0.95), "diag_b", 0.84)]


def paint_hyperflip_orange_cyan(paint, shape, mask, seed, pm, bb):
    def _rings(color, hw, sd, pm_, gate, msk):
        pulse = _geo_orange_rings(hw, sd)
        w = (pulse * gate) * (0.35 * pm_) * msk
        return _hf_add_accent(color, (1.0, 0.55, 0.08), w)

    return _hf_paint_reveal(
        paint, shape, mask, seed, pm, 9103,
        (0.92, 0.38, 0.04), (0.05, 0.04, 0.04),
        _REVEALS_9103,
        mist_colors=[(0.02, 0.82, 0.95), (0.98, 0.42, 0.02)],
        extra=lambda c, hw, sd, pm_, gate, msk: _rings(c, hw, sd, pm_, gate, msk),
    )


def spec_hyperflip_orange_cyan(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    pulse = _geo_orange_rings((h, w), seed)
    flash, gate, _ = _hf_reveal_flash(shape, seed, 9103, _REVEALS_9103)
    da = _hf_axis((h, w), "diag_a", seed + 9103)
    db = _hf_axis((h, w), "diag_b", seed + 9203)
    rings = pulse * gate
    flash = np.clip(rings * (da * 0.52 + db * 0.48) * 0.76 + flash * 0.24, 0, 1)
    pins = _cx_fine_spec_pins((h, w), seed, 9103, density=0.0092, layers=6) * rings
    M, R, CC = _hf_marry_spec(flash, sm, m_hi=235, pin=pins, cc_mod=rings * 24.0)
    return _pack_spec(M, R, CC, mask, shape)


# ── 9104 Lime/Purple — honeycomb cell gate ────────────────────────────────

_REVEALS_9104 = [((0.42, 0.98, 0.08), "u", 0.88), ((0.58, 0.06, 0.95), "v", 0.84)]


def paint_hyperflip_lime_purple(paint, shape, mask, seed, pm, bb):
    def _hex(color, hw, sd, pm_, gate, msk):
        hex_gate = _hf_hex_gate(hw, sd, 9104)
        lime = np.array([0.42, 0.98, 0.08], dtype=np.float32).reshape(1, 1, 3)
        violet = np.array([0.58, 0.06, 0.95], dtype=np.float32).reshape(1, 1, 3)
        u = _hf_axis(hw, "u", sd + 9104)
        v = _hf_axis(hw, "v", sd + 9204)
        # fold scalar weights to HxW, then two broadcast-adds with ONE final clip
        hgm = hex_gate * msk
        wl = (hgm * u) * (0.32 * pm_)
        wv = (hgm * v) * (0.28 * pm_)
        color += lime * wl[:, :, np.newaxis]
        color += violet * wv[:, :, np.newaxis]
        np.clip(color, 0, 1, out=color)
        return color

    return _hf_paint_reveal(
        paint, shape, mask, seed, pm, 9104,
        (0.38, 0.88, 0.12), (0.08, 0.10, 0.06),
        _REVEALS_9104,
        mist_colors=[(0.42, 0.98, 0.08), (0.58, 0.06, 0.95)],
        extra=lambda c, hw, sd, pm_, gate, msk: _hex(c, hw, sd, pm_, gate, msk),
    )


def spec_hyperflip_lime_purple(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    hex_gate = _hf_hex_gate((h, w), seed, 9104)
    flash, gate, _ = _hf_reveal_flash(shape, seed, 9104, _REVEALS_9104)
    u = _hf_axis((h, w), "u", seed + 9104)
    v = _hf_axis((h, w), "v", seed + 9204)
    cells = hex_gate * gate
    flash = np.clip(cells * (u * 0.55 + v * 0.45) * 0.74 + flash * 0.26, 0, 1)
    M, R, CC = _hf_marry_spec(flash, sm, m_hi=228, pin=cells, r_mod=-cells * u * 22.0, cc_mod=cells * v * 26.0)
    return _pack_spec(M, R, CC, mask, shape)


# ── 9105 Purple/Gold — filigree rosette dust on tri-axis reveal ───────────

_REVEALS_9105 = [
    ((0.48, 0.08, 0.82), "u", 0.90), ((0.98, 0.78, 0.12), "v", 0.86),
    ((0.92, 0.62, 0.22), "diag_a", 0.62),
]


def paint_hyperflip_purple_gold(paint, shape, mask, seed, pm, bb):
    def _rosette(color, hw, sd, pm_, gate, msk):
        rosette = _geo_purple_rosette(hw, sd)
        w = (rosette * (0.48 * pm_)) * msk
        return _hf_add_accent(color, (1.0, 0.86, 0.18), w)

    return _hf_paint_reveal(
        paint, shape, mask, seed, pm, 9105,
        (0.42, 0.10, 0.72), (0.08, 0.05, 0.10),
        _REVEALS_9105,
        mist_colors=[(0.98, 0.78, 0.12), (0.48, 0.08, 0.82), (0.92, 0.62, 0.22)],
        extra=lambda c, hw, sd, pm_, gate, msk: _rosette(c, hw, sd, pm_, gate, msk),
    )


def spec_hyperflip_purple_gold(shape, mask, seed, sm):
    rosette = _geo_purple_rosette(shape, seed)
    flash, gate, _ = _hf_reveal_flash(shape, seed, 9105, _REVEALS_9105)
    h, w = _shape_hw(shape)
    u = _hf_axis((h, w), "u", seed + 9105)
    v = _hf_axis((h, w), "v", seed + 9205)
    da = _hf_axis((h, w), "diag_a", seed + 9305)
    dust = rosette * gate
    flash = np.clip(dust * (u * 0.38 + v * 0.34 + da * 0.28) * 0.76 + flash * 0.24, 0, 1)
    M, R, CC = _hf_marry_spec(flash, sm, m_hi=245, pin=dust, cc_mod=dust * 36.0, r_mod=-dust * v * 18.0)
    return _pack_spec(M, R, CC, mask, shape)


# ── 9106 Electric Blue/Copper — welder filament arcs ──────────────────────

_REVEALS_9106 = [((0.05, 0.22, 0.98), "v", 0.90), ((0.92, 0.48, 0.08), "u", 0.86)]


def paint_hyperflip_electric_blue_copper(paint, shape, mask, seed, pm, bb):
    def _arcs(color, hw, sd, pm_, gate, msk):
        arc = _geo_blue_copper_arcs(hw, sd)
        copper = np.array([0.98, 0.55, 0.12], dtype=np.float32).reshape(1, 1, 3)
        blue = np.array([0.12, 0.42, 0.98], dtype=np.float32).reshape(1, 1, 3)
        mix = (arc * gate) * msk
        wc = mix * (0.42 * pm_)
        wb = mix * (0.28 * pm_)
        color += copper * wc[:, :, np.newaxis]
        color += blue * wb[:, :, np.newaxis]
        np.clip(color, 0, 1, out=color)
        return color

    return _hf_paint_reveal(
        paint, shape, mask, seed, pm, 9106,
        (0.10, 0.28, 0.88), (0.05, 0.08, 0.14),
        _REVEALS_9106,
        mist_colors=[(0.92, 0.48, 0.08), (0.05, 0.22, 0.98), (0.98, 0.72, 0.18)],
        extra=lambda c, hw, sd, pm_, gate, msk: _arcs(c, hw, sd, pm_, gate, msk),
    )


def spec_hyperflip_electric_blue_copper(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    arc = _geo_blue_copper_arcs((h, w), seed)
    flash, gate, _ = _hf_reveal_flash(shape, seed, 9106, _REVEALS_9106)
    u = _hf_axis((h, w), "u", seed + 9106)
    v = _hf_axis((h, w), "v", seed + 9206)
    weld = arc * gate
    flash = np.clip(weld * (u * 0.58 + v * 0.42) * 0.78 + flash * 0.22, 0, 1)
    pins = _cx_fine_spec_pins((h, w), seed, 9106, density=0.0094, layers=6) * weld
    M, R, CC = _hf_marry_spec(flash, sm, m_hi=242, pin=pins, cc_mod=weld * 32.0, r_mod=-arc * u * 24.0)
    return _pack_spec(M, R, CC, mask, shape)


# ── 9107 Bronze/Teal — horizontal scan-line reveal ──────────────────────

_REVEALS_9107 = [((0.78, 0.42, 0.12), "u", 0.88), ((0.02, 0.78, 0.72), "v", 0.84)]


def paint_hyperflip_bronze_teal(paint, shape, mask, seed, pm, bb):
    def _scan(color, hw, sd, pm_, gate, msk):
        scan = _geo_bronze_scan(hw, sd)
        bronze = np.array([0.78, 0.42, 0.12], dtype=np.float32).reshape(1, 1, 3)
        teal = np.array([0.02, 0.78, 0.72], dtype=np.float32).reshape(1, 1, 3)
        u = _hf_axis(hw, "u", sd + 9107)
        v = _hf_axis(hw, "v", sd + 9207)
        # fold all scalar fields to HxW before the single 3-channel broadcast adds
        mix = (gate * scan) * msk
        wb = (mix * u) * (0.34 * pm_)
        wt = (mix * (1.0 - scan) * v) * (0.30 * pm_)
        color += bronze * wb[:, :, np.newaxis]
        color += teal * wt[:, :, np.newaxis]
        np.clip(color, 0, 1, out=color)
        return color

    return _hf_paint_reveal(
        paint, shape, mask, seed, pm, 9107,
        (0.72, 0.38, 0.10), (0.10, 0.08, 0.06),
        _REVEALS_9107,
        mist_colors=[(0.78, 0.42, 0.12), (0.02, 0.78, 0.72)],
        extra=lambda c, hw, sd, pm_, gate, msk: _scan(c, hw, sd, pm_, gate, msk),
    )


def spec_hyperflip_bronze_teal(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    scan = _geo_bronze_scan((h, w), seed)
    flash, gate, _ = _hf_reveal_flash(shape, seed, 9107, _REVEALS_9107)
    u = _hf_axis((h, w), "u", seed + 9107)
    v = _hf_axis((h, w), "v", seed + 9207)
    lines = scan * gate
    aniso = lines * u + (1.0 - scan) * lines * v
    flash = np.clip(aniso * 0.88 + flash * 0.12, 0, 1)
    pins = _cx_fine_spec_pins((h, w), seed, 9107, density=0.0070, layers=5) * lines
    M, R, CC = _hf_marry_spec(flash, sm, pin=pins, r_mod=(1.0 - scan) * 32.0 - aniso * 52.0, cc_mod=-aniso * 38.0)
    M = np.clip(M + scan * 28.0 * sm + lines * 18.0 * sm, 0, 255)
    return _pack_spec(M, R, CC, mask, shape)


# ── 9108 Silver/Violet — frost pearl, CC-forward spec ─────────────────────

_REVEALS_9108 = [((0.82, 0.84, 0.88), "u", 0.84), ((0.62, 0.12, 0.95), "v", 0.82)]


def paint_hyperflip_silver_violet(paint, shape, mask, seed, pm, bb):
    def _frost(color, hw, sd, pm_, gate, msk):
        sheen = _geo_silver_frost(hw, sd)
        cool = np.array([0.88, 0.90, 0.98], dtype=np.float32)
        violet = np.array([0.62, 0.12, 0.95], dtype=np.float32)
        m3 = msk[:, :, np.newaxis]
        return np.clip(
            color * (1.0 + sheen[:, :, np.newaxis] * 0.10 * pm_ * m3)
            + cool.reshape(1, 1, 3) * sheen[:, :, np.newaxis] * 0.14 * pm_ * m3
            + violet.reshape(1, 1, 3) * gate[:, :, np.newaxis] * sheen[:, :, np.newaxis] * 0.22 * pm_ * m3,
            0, 1,
        )

    return _hf_paint_reveal(
        paint, shape, mask, seed, pm, 9108,
        (0.72, 0.74, 0.78), (0.12, 0.12, 0.14),
        _REVEALS_9108,
        mist_colors=[(0.62, 0.12, 0.95), (0.82, 0.84, 0.88)],
        extra=lambda c, hw, sd, pm_, gate, msk: _frost(c, hw, sd, pm_, gate, msk),
    )


def spec_hyperflip_silver_violet(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    sheen = _geo_silver_frost((h, w), seed)
    flash, gate, micro = _hf_reveal_flash(shape, seed, 9108, _REVEALS_9108)
    v = _hf_axis((h, w), "v", seed + 91084)
    frost = np.clip(sheen * gate * 0.72 + flash * 0.28, 0, 1)
    pins = _cx_fine_spec_pins((h, w), seed, 9108, density=0.0076, layers=6) * np.clip(sheen, 0, 1)
    sparkle = np.clip(pins * 0.68 + np.clip((micro - 0.62) * 3.0, 0, 1) * 0.32, 0, 1)
    flash = np.clip(frost * 0.62 + sparkle * 0.38, 0, 1)
    M = 12.0 + flash * 228.0 * sm + (1.0 - sparkle) * 18.0 * sm
    R = 165.0 - flash * 128.0 * sm - pins * 24.0 * sm + v * 8.0 * sm
    CC = 148.0 - flash * 128.0 * sm + pins * 52.0 * sm + sheen * gate * 18.0 * sm
    return _pack_spec(M, R, CC, mask, shape)


# ── 9109 Crimson Prism — quad-axis four-color reveal ──────────────────────

_REVEALS_9109 = [
    ((0.92, 0.04, 0.08), "u", 0.90), ((0.02, 0.82, 0.98), "v", 0.86),
    ((0.98, 0.76, 0.08), "diag_a", 0.76), ((0.68, 0.08, 0.95), "diag_b", 0.72),
]


def paint_hyperflip_crimson_prism(paint, shape, mask, seed, pm, bb):
    return _hf_paint_reveal(
        paint, shape, mask, seed, pm, 9109,
        (0.82, 0.05, 0.08), (0.08, 0.04, 0.05),
        _REVEALS_9109,
        gate_density=0.0120,
        mist_colors=[(0.92, 0.04, 0.08), (0.02, 0.82, 0.98), (0.98, 0.76, 0.08), (0.68, 0.08, 0.95)],
    )


def spec_hyperflip_crimson_prism(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    flash, gate, micro = _hf_reveal_flash(shape, seed, 9109, _REVEALS_9109, gate_density=0.0120)
    u = _hf_axis((h, w), "u", seed + 9109) * gate
    v = _hf_axis((h, w), "v", seed + 9209) * gate
    da = _hf_axis((h, w), "diag_a", seed + 9309) * gate
    db = _hf_axis((h, w), "diag_b", seed + 9409) * gate
    pins = _cx_fine_spec_pins((h, w), seed, 9109, density=0.0098, layers=6) * gate
    prism = np.clip(u * 0.30 + v * 0.26 + da * 0.24 + db * 0.20, 0, 1)
    flash = np.clip(prism * 0.76 + flash * 0.24, 0, 1)
    M, R, CC = _hf_marry_spec(
        flash, sm, m_lo=8, m_hi=245, r_lo=192, pin=pins,
        r_mod=-u * 18.0 + v * 12.0 + da * 8.0,
        cc_mod=pins * 22.0 + np.clip((micro - 0.55) * 2.0, 0, 1) * 14.0,
    )
    M = np.clip(M + prism * 36.0 * sm, 0, 255)
    return _pack_spec(M, R, CC, mask, shape)


# ── 9110 Midnight Opal — dark quad reveal + opal pin fire ─────────────────

_REVEALS_9110 = [
    ((0.98, 0.48, 0.10), "u", 0.86), ((0.38, 0.98, 0.08), "v", 0.82),
    ((0.98, 0.08, 0.68), "diag_a", 0.76), ((0.22, 0.42, 0.95), "diag_b", 0.68),
]


def paint_hyperflip_midnight_opal(paint, shape, mask, seed, pm, bb):
    def _opal(color, hw, sd, pm_, gate, msk):
        opal_pins = _geo_midnight_opal_pins(hw, sd)
        palette = np.array([
            [1.0, 0.55, 0.12], [0.35, 0.98, 0.15], [0.98, 0.15, 0.72], [0.45, 0.72, 1.0],
        ], dtype=np.float32)
        opal_h = _hf_hash01(hw, sd, 91101)
        idx = np.clip(np.floor(opal_h * 4.0).astype(np.int32), 0, 3)
        w = (opal_pins * (0.45 * pm_)) * msk
        color += palette[idx] * w[:, :, np.newaxis]
        np.clip(color, 0, 1, out=color)
        return color

    return _hf_paint_reveal(
        paint, shape, mask, seed, pm, 9110,
        (0.08, 0.10, 0.22), (0.02, 0.03, 0.08),
        _REVEALS_9110,
        gate_density=0.0118,
        mist_colors=[(0.98, 0.48, 0.10), (0.38, 0.98, 0.08), (0.98, 0.08, 0.68), (0.22, 0.42, 0.95)],
        extra=lambda c, hw, sd, pm_, gate, msk: _opal(c, hw, sd, pm_, gate, msk),
    )


def spec_hyperflip_midnight_opal(shape, mask, seed, sm):
    h, w = _shape_hw(shape)
    opal_pins = _geo_midnight_opal_pins((h, w), seed)
    flash, gate, _ = _hf_reveal_flash(shape, seed, 9110, _REVEALS_9110, gate_density=0.0118)
    h2 = _hf_hash01((h, w), seed, 91103)
    fire = np.clip((h2 - 0.5) * 2.0, 0, 1) * opal_pins * gate
    opal = np.clip(opal_pins * gate * 0.68 + flash * 0.32, 0, 1)
    M = 6.0 + opal * 198.0 * sm + fire * 58.0 * sm
    R = 205.0 - opal * 178.0 * sm + fire * 18.0 * sm
    CC = 188.0 - fire * 168.0 * sm + opal * 52.0 * sm
    return _pack_spec(M, R, CC, mask, shape)


HYPERFLIP_ANGLE_REVEAL = {
    "cx_hyperflip_red_blue": (spec_hyperflip_red_blue, paint_hyperflip_red_blue),
    "cx_hyperflip_pink_black": (spec_hyperflip_pink_black, paint_hyperflip_pink_black),
    "cx_hyperflip_orange_cyan": (spec_hyperflip_orange_cyan, paint_hyperflip_orange_cyan),
    "cx_hyperflip_lime_purple": (spec_hyperflip_lime_purple, paint_hyperflip_lime_purple),
    "cx_hyperflip_purple_gold": (spec_hyperflip_purple_gold, paint_hyperflip_purple_gold),
    "cx_hyperflip_electric_blue_copper": (spec_hyperflip_electric_blue_copper, paint_hyperflip_electric_blue_copper),
    "cx_hyperflip_bronze_teal": (spec_hyperflip_bronze_teal, paint_hyperflip_bronze_teal),
    "cx_hyperflip_silver_violet": (spec_hyperflip_silver_violet, paint_hyperflip_silver_violet),
    "cx_hyperflip_crimson_prism": (spec_hyperflip_crimson_prism, paint_hyperflip_crimson_prism),
    "cx_hyperflip_midnight_opal": (spec_hyperflip_midnight_opal, paint_hyperflip_midnight_opal),
}

from engine.colorshoxx_spectrum_pop import HYPERFLIP_SPECTRUM_POP  # noqa: E402

HYPERFLIP_ANGLE_REVEAL.update(HYPERFLIP_SPECTRUM_POP)
