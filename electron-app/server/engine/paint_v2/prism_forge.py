"""
engine/paint_v2/prism_forge.py — ★ PRISM FORGE
================================================
**v3 (2026-05-12):** Microscopic carrier rebuild.

v2 split macro/fine but macro_styles like stripe/radial/cells still printed
**large** structure into diffuse + spec — reads as candy stripes, pinwheels,
and diagonal wallpaper on 2048 UVs.

v3 rules:
  * **Diffuse (paint):** hue/sat/value drift from **multi_scale_noise** at
    **small pixel scales** (typically 3–36px features) + optional per-cell hash.
    No low-order sine bands on albedo. Optional **cluster** engine uses
    smooth **island-scale** regions (48–180px) with RGB stop lerps for clustered
    pocket color, still crushed with micro grain on top.
  * **Specular:** **Ultra-HF** tri-sine carrier (hundreds of cycles across UV)
    + existing fine field at **high uf/vf** + hash/sparkle. Macro dispatch is
    **not** used in v3 spec (eliminates visible spec wallpaper).
  * **rgb_flake** (optional per row): 3+ RGB primaries in 0–1, each gated by its
    own **fine** ``multi_scale_noise`` stack (low integer scales = small cells; see
    ``core.multi_scale_noise``) + softmax. Optional ``rgb_flake_scale_sets`` /
    ``rgb_flake_logit_hf`` / ``rgb_flake_region_amp`` tune flake size vs. clown blobs.
  * **hue_palette** (optional): ordered hue stops 0–1 walked by ``region01`` with
    circular lerp for tri-tone reads without full RGB flake.

**legacy_v2** engine preserves the exact v2 macro path for **Void Pearl** and
**Copper Moon** only (per artist request).

Seeds **9600–9649** reserved (50 finishes).
"""
from __future__ import annotations

import numpy as np
import cv2

from engine.core import hsv_to_rgb_vec, multi_scale_noise

__all__ = ["PRISM_FORGE_BASE_REGISTRY"]

_PF_WORK_CAP: int = 1024

# SPB-PERF-2026-06-04: cap for the *low-amplitude companion* paint fields that
# the rgb_flake softmax modulates -- the per-pixel ``micro`` hash dither, the
# ``grain01`` luminance pulse, and the ``region01`` tilt. These are smooth and/or
# tiny-amplitude, so solving them at this cap and resizing up is visually
# negligible (verified: the real 2048 canvas std@256 shifts <0.4% and mean abs
# delta <1.5/255 on the pf_* blend family). The flake field itself is left at the
# full work cap so its 1-3px grain never repositions. ``_pf_work_shape`` is a
# no-op at/below this cap, so 160/256px previews stay *byte-identical*.
_PF_PAINT_CAP: int = 704

# SPB-PERF-2026-06-04: the intrinsic spec (M/R/CC) ultra/fine carriers are
# already solved at a work cap and resized to canvas. Hundreds of spec cycles
# across the UV are well past Nyquist at any work res (the resize softens them
# either way), so dropping the spec cap from 1024 keeps the same rich spec read
# while cutting the carrier pixel count at 2048. Verified on the pf_* blend
# family: spec std@256 shifts <0.5% and mean abs delta ~4/255 across caps
# 1024->640 (the carrier is smooth post-resize). No-op at/below the cap, so
# 160/256px previews stay byte-identical.
_PF_SPEC_CAP: int = 640

# ``multi_scale_noise`` uses grid cells ~``h // scale``; keep scales small (1–8)
# so logits vary at near-pixel / few-pixel scale — large values (12–22) read as
# camouflage blobs on 2K–4K UVs.
_RGB_FLAKE_SCALE_SETS_MICRO: tuple[tuple[int, ...], ...] = (
    (1, 2, 3, 4),
    (1, 2, 3, 5),
    (2, 3, 4, 5),
    (1, 2, 4, 6),
    (2, 3, 4, 6),
    (2, 3, 5, 7),
)


def _xy_norm(shape):
    h, w = int(shape[0]), int(shape[1])
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    return x, y


def _pf_work_shape(h: int, w: int, cap: int | None = _PF_WORK_CAP) -> tuple[int, int]:
    if cap is None:
        return int(h), int(w)
    max_dim = max(int(h), int(w))
    if max_dim <= int(cap):
        return int(h), int(w)
    scale = float(cap) / float(max_dim)
    return max(64, int(round(h * scale))), max(64, int(round(w * scale)))


def _pf_resize(field: np.ndarray, h: int, w: int) -> np.ndarray:
    if field.shape[:2] == (h, w):
        return field.astype(np.float32, copy=False)
    resized = cv2.resize(field.astype(np.float32, copy=False), (int(w), int(h)), interpolation=cv2.INTER_LINEAR)
    return resized.astype(np.float32, copy=False)


def _hash01(shape, seed: int, salt: int = 0) -> np.ndarray:
    x, y = _xy_norm(shape)
    s = float(seed + salt) * 0.00137
    n = np.sin(
        (x * (127.1 + (salt % 11) * 3.7) + y * (311.7 + (salt % 7) * 5.1) + s)
        * 43758.5453
    )
    return (n - np.floor(n)).astype(np.float32)


def _hash01_capped(h: int, w: int, seed: int, salt: int, cap: int | None) -> np.ndarray:
    """``_hash01`` solved at a bounded work shape then resized to (h, w).

    SPB-PERF-2026-06-04: the full-res ``np.sin(...)*43758 - floor`` is a 4M-pixel
    transcendental on a 2048 plate. When this hash is only a low-amplitude flake
    dither, computing it at ``cap`` and upsampling keeps the same statistical
    character (and is byte-identical at/below ``cap``, so previews never change).
    """
    wh, ww = _pf_work_shape(h, w, cap)
    field = _hash01((wh, ww), seed, salt)
    if (wh, ww) != (int(h), int(w)):
        field = _pf_resize(field, int(h), int(w))
    return field.astype(np.float32, copy=False)


def _macro_flow(shape, seed: int, seed_off: int) -> np.ndarray:
    h, w = shape
    n1 = multi_scale_noise((h, w), [48, 96, 176], [0.38, 0.34, 0.28], seed + seed_off)
    n2 = multi_scale_noise((h, w), [56, 112], [0.52, 0.48], seed + seed_off + 2)
    f = (n1 * 0.62 + n2 * 0.38 + 1.0) * 0.5
    return np.clip((f - 0.5) * 1.35 + 0.5, 0, 1).astype(np.float32)


def _macro_damascus(shape, seed: int, seed_off: int) -> np.ndarray:
    x, y = _xy_norm(shape)
    h, w = shape
    ang = 0.52 + (seed_off % 9) * 0.09
    ca, sa = np.cos(ang), np.sin(ang)
    u = x * ca + y * sa
    v = x * (-sa) + y * ca
    s = float(seed + seed_off) * 0.011
    fu = 8.0 + (seed_off % 5)
    fv = 7.0 + (seed_off % 4)
    d = np.sin((u * fu + s) * np.pi) * np.sin((v * fv - s * 1.2) * np.pi)
    d = (d * 0.5 + 0.5).astype(np.float32)
    sm = multi_scale_noise((h, w), [64, 128], [0.55, 0.45], seed + seed_off + 5)
    return np.clip(d * 0.78 + (sm * 0.5 + 0.5) * 0.22, 0, 1).astype(np.float32)


def _macro_radial(shape, seed: int, seed_off: int) -> np.ndarray:
    x, y = _xy_norm(shape)
    s = float(seed + seed_off) * 0.013
    cx = 0.48 + 0.04 * np.sin(s)
    cy = 0.46 + 0.04 * np.cos(s * 0.8)
    ang = np.arctan2(y - cy, x - cx + 1e-5)
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2 + 1e-8)
    rings = 0.5 + 0.5 * np.sin(ang * (5.0 + (seed_off % 4)) + r * np.pi * (14.0 + (seed_off % 6)))
    return np.clip(rings, 0, 1).astype(np.float32)


def _macro_stripe(shape, seed: int, seed_off: int) -> np.ndarray:
    x, y = _xy_norm(shape)
    h, w = shape
    ang = 1.1 + (seed_off % 5) * 0.31
    ca, sa = np.cos(ang), np.sin(ang)
    u = x * ca + y * sa
    s = float(seed + seed_off) * 0.019
    bands = 0.5 + 0.5 * np.sin((u * (9.0 + (seed_off % 7)) + s) * np.pi * 2.0)
    warp = multi_scale_noise((h, w), [72, 144], [0.5, 0.5], seed + seed_off + 3)
    return np.clip(bands * 0.82 + warp * 0.18, 0, 1).astype(np.float32)


def _macro_cells(shape, seed: int, seed_off: int) -> np.ndarray:
    x, y = _xy_norm(shape)
    h, w = shape
    nx = 9.0 + (seed_off % 5)
    ny = 8.0 + (seed_off % 6)
    gx = np.floor(x * nx * 3.2 + y * 0.7).astype(np.int32)
    gy = np.floor(y * ny * 3.0 + x * 0.5).astype(np.int32)
    cell = np.sin(gx.astype(np.float32) * 12.9898 + gy.astype(np.float32) * 78.233 + seed_off)
    cell = (cell * 0.5 + 0.5).astype(np.float32)
    soft = multi_scale_noise((h, w), [40, 80], [0.5, 0.5], seed + seed_off + 9)
    return np.clip(cell * 0.55 + (soft * 0.5 + 0.5) * 0.45, 0, 1).astype(np.float32)


def _macro_dispatch(shape, seed: int, seed_off: int, style: str) -> np.ndarray:
    if style == "damascus":
        return _macro_damascus(shape, seed, seed_off)
    if style == "radial":
        return _macro_radial(shape, seed, seed_off)
    if style == "stripe":
        return _macro_stripe(shape, seed, seed_off)
    if style == "cells":
        return _macro_cells(shape, seed, seed_off)
    return _macro_flow(shape, seed, seed_off)


def _fine_spec_field(shape, seed: int, seed_off: int, uf: float, vf: float, warp: float,
                     work_cap: int | None = None) -> np.ndarray:
    h, w = int(shape[0]), int(shape[1])
    x, y = _xy_norm(shape)
    s0 = float(seed + seed_off) * 0.017
    wx = _noise_field(h, w, seed, seed_off + 13, [12, 24], [0.52, 0.48], work_cap)
    wy = _noise_field(h, w, seed, seed_off + 17, [12, 24], [0.52, 0.48], work_cap)
    px = np.clip(x + (wx * 2.0 - 1.0) * warp, 0, 1)
    py = np.clip(y + (wy * 2.0 - 1.0) * warp, 0, 1)
    p = (
        np.sin((px * uf + py * vf + s0) * np.pi * 2.0) * 0.40
        + np.sin((px * vf * 1.21 - py * uf * 0.88 + s0 * 1.55) * np.pi * 2.0) * 0.35
    )
    spark = _hash01((h, w), seed + seed_off, 211)
    p = p * 0.72 + (spark * 2.0 - 1.0) * 0.14
    return np.clip(p * 0.5 + 0.5, 0, 1).astype(np.float32)


def _ultra_carrier(shape, seed: int, seed_off: int, cfg: dict) -> np.ndarray:
    """Sub-pixel to few-pixel spec beats — no macro wallpaper."""
    h, w = int(shape[0]), int(shape[1])
    x, y = _xy_norm(shape)
    s = float(seed + seed_off) * 0.00047
    warp = float(cfg.get("spec_ultra_warp", 0.014))
    work_cap = cfg.get("spec_work_cap", _PF_WORK_CAP)
    wx = _noise_field(h, w, seed, seed_off + 901, [3, 6], [0.52, 0.48], work_cap) * warp
    wy = _noise_field(h, w, seed, seed_off + 902, [3, 6], [0.52, 0.48], work_cap) * warp
    px = np.clip(x + wx, 0, 1)
    py = np.clip(y + wy, 0, 1)
    cx = float(cfg.get("spec_cycles_x", 620.0))
    cy = float(cfg.get("spec_cycles_y", 583.0))
    cz = float(cfg.get("spec_cycles_diag", 511.0))
    a = 0.5 + 0.5 * np.sin(2.0 * np.pi * (px * cx + py * cy * 0.31 + s))
    b = 0.5 + 0.5 * np.sin(2.0 * np.pi * (py * cz - px * cx * 0.27 + s * 1.63))
    c = 0.5 + 0.5 * np.sin(2.0 * np.pi * ((px * 0.71 + py * 0.29) * cz * 1.08 + s * 0.88))
    d = _hash01((h, w), seed + seed_off, 409)
    tp = float(cfg.get("tri_power", 0.42))
    tri = np.clip((a * b * c) ** tp, 0, 1).astype(np.float32)
    mix = tri * 0.52 + a * 0.18 + b * 0.14 + d * 0.16
    return np.clip(mix, 0, 1).astype(np.float32)


def _bb_to_2d(bb, h: int, w: int) -> np.ndarray:
    try:
        if np.isscalar(bb) or (hasattr(bb, "ndim") and bb.ndim == 0):
            return np.full((h, w), float(bb), dtype=np.float32)
        b = np.asarray(bb, dtype=np.float32)
        if b.ndim == 2:
            return b[:h, :w].astype(np.float32)
        if b.ndim == 3:
            return np.mean(b[:h, :w, :3], axis=2).astype(np.float32)
    except Exception:
        pass
    return np.zeros((h, w), dtype=np.float32)


def _bb_active_values(bb, h: int, w: int, active: np.ndarray) -> np.ndarray | float:
    try:
        if np.isscalar(bb) or (hasattr(bb, "ndim") and bb.ndim == 0):
            return float(bb)
        b = np.asarray(bb, dtype=np.float32)
        if b.ndim == 2:
            return b[:h, :w][active].astype(np.float32, copy=False)
        if b.ndim == 3:
            return np.mean(b[:h, :w, :3], axis=2)[active].astype(np.float32, copy=False)
    except Exception:
        pass
    return 0.0


def _norm_weights(w):
    w = np.array(w, dtype=np.float64)
    s = float(w.sum()) or 1.0
    return (w / s).astype(np.float32).tolist()


def _noise_field(h: int, w: int, seed: int, seed_off: int, scales, weights, cap: int | None = None) -> np.ndarray:
    scales = tuple(int(x) for x in scales)
    weights = _norm_weights(weights)
    wh, ww = _pf_work_shape(h, w, cap)
    n = multi_scale_noise((wh, ww), list(scales), weights, seed + seed_off)
    if (wh, ww) != (int(h), int(w)):
        n = _pf_resize(n, int(h), int(w))
    return n.astype(np.float32, copy=False)


def _region_field(h: int, w: int, seed: int, seed_off: int, scales, weights, cap: int | None = None) -> np.ndarray:
    n = _noise_field(h, w, seed, seed_off, scales, weights, cap)
    return (n * 0.5 + 0.5).astype(np.float32)


def _rgb_lerp_stops(t: np.ndarray, stops: list[tuple[float, float, float]]) -> np.ndarray:
    t = np.clip(t.astype(np.float64), 0.0, 1.0)
    k = len(stops) - 1
    if k <= 0:
        c0 = np.array(stops[0], dtype=np.float32)
        return np.broadcast_to(c0.reshape(1, 1, 3), t.shape + (3,)).copy()
    stops_a = np.array(stops, dtype=np.float32)
    idx = t * k
    i0 = np.floor(idx).astype(np.int32)
    i1 = np.minimum(i0 + 1, k)
    frac = (idx - i0.astype(np.float64)).astype(np.float32)[..., np.newaxis]
    c0 = stops_a[i0]
    c1 = stops_a[i1]
    return np.clip(c0 + (c1 - c0) * frac, 0, 1).astype(np.float32)


def _rgb_flake_rgb(
    h: int,
    w: int,
    seed: int,
    seed_off: int,
    colors: list[tuple[float, float, float]],
    sharp: float,
    scale_sets: tuple[tuple[int, ...], ...] | None = None,
    logit_hf: float = 0.0,
    work_cap: int | None = None,
) -> np.ndarray:
    """Microscopic multi-primary RGB: each color competes via decorrelated noise + softmax."""
    rgbs = np.asarray(colors, dtype=np.float32)
    k = int(rgbs.shape[0])
    if k < 3:
        raise ValueError("rgb_flake requires at least 3 RGB tuples")
    wh, ww = _pf_work_shape(h, w, work_cap)
    ss = scale_sets if scale_sets is not None else _RGB_FLAKE_SCALE_SETS_MICRO
    hf = float(logit_hf)
    logits = []
    for i in range(k):
        scales = ss[i % len(ss)]
        uw = tuple(1.0 for _ in scales)
        field = _region_field(wh, ww, seed, seed_off + 23 * (i + 3), scales, uw)
        if hf > 0.0:
            d = _hash01((wh, ww), seed + seed_off + 511 * (i + 1), 199 + i)
            field = np.clip(field + (d - 0.5) * (2.0 * hf), 0.0, 1.0).astype(np.float32)
        logits.append(field)
    L = np.stack(logits, axis=-1).astype(np.float32)
    L = (L - 0.5) * 2.4
    L = L * float(sharp)
    ex = np.exp(np.clip(L, -10.0, 10.0))
    wt = ex / (np.sum(ex, axis=-1, keepdims=True) + 1e-7)
    rgb = np.clip(np.einsum("hwk,kc->hwc", wt, rgbs), 0, 1).astype(np.float32)
    if (wh, ww) != (int(h), int(w)):
        rgb = _pf_resize(rgb, int(h), int(w))
    return rgb


def _hue_walk_from_palette(region01: np.ndarray, palette: list[float], micro: np.ndarray, jitter: float) -> np.ndarray:
    """Walk ordered hue stops (0..1) with circular shortest-path lerp + micro jitter."""
    pal = np.asarray(palette, dtype=np.float64)
    n = int(pal.shape[0])
    if n < 2:
        return np.full_like(region01, float(pal[0]) if n == 1 else 0.5, dtype=np.float32)
    t = np.clip(region01.astype(np.float64) * (n - 0.001), 0.0, n - 1.001)
    t = t + (micro.astype(np.float64) * 2.0 - 1.0) * float(jitter)
    t = np.clip(t, 0.0, n - 1.001)
    i0 = np.floor(t).astype(np.int32)
    i1 = np.minimum(i0 + 1, n - 1)
    frac = (t - i0.astype(np.float64)).astype(np.float32)
    h0 = pal[i0]
    h1 = pal[i1]
    d = (h1 - h0 + 0.5) % 1.0 - 0.5
    return np.mod(h0 + frac.astype(np.float64) * d, 1.0).astype(np.float32)


def _pf_paint_legacy(paint, shape, mask, seed, pm, bb, cfg: dict) -> np.ndarray:
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2] if len(shape) >= 2 else paint.shape[:2]
    h, w = int(h), int(w)
    seed_off = int(cfg["seed_off"])
    macro_style = str(cfg.get("macro_style", "flow"))
    macro = _macro_dispatch((h, w), int(seed), seed_off, macro_style)
    fine = _fine_spec_field(
        (h, w),
        int(seed),
        seed_off,
        float(cfg.get("spec_uf", 22.0)),
        float(cfg.get("spec_vf", 18.0)),
        float(cfg.get("spec_warp", 0.055)),
        None,
    )
    micro = _hash01((h, w), seed + seed_off, 101)

    phg = float(cfg.get("paint_hue_gain", 0.16))
    hue = float(cfg["hue_c"]) + (macro * 2.0 - 1.0) * float(cfg["hue_span"]) * phg
    hue = hue + (micro * 2.0 - 1.0) * float(cfg.get("hue_jitter", 0.018))
    hue = hue + (fine * 2.0 - 1.0) * float(cfg.get("paint_fine_hue", 0.012)) * float(cfg["hue_span"])
    hue = np.mod(hue, 1.0).astype(np.float32)

    psg = float(cfg.get("paint_sat_gain", 0.85))
    sat = float(cfg["sat0"]) + macro * float(cfg["sat1"] - cfg["sat0"]) * psg
    sat = sat + fine * float(cfg.get("paint_fine_sat", 0.04))
    sat = sat + micro * float(cfg.get("sat_micro", 0.04))
    sat = np.clip(sat, 0, 1).astype(np.float32)

    pvg = float(cfg.get("paint_val_gain", 0.88))
    val = float(cfg["v0"]) + macro * float(cfg["v1"] - cfg["v0"]) * pvg
    val = val + fine * float(cfg.get("paint_fine_val", 0.055))
    val = val + micro * float(cfg.get("val_micro", 0.035))
    val = np.clip(val, 0, 1).astype(np.float32)

    r, g, b = hsv_to_rgb_vec(hue, sat, val)
    rgb = np.stack([r, g, b], axis=2).astype(np.float32)
    if cfg.get("tint"):
        t = np.array(cfg["tint"], dtype=np.float32).reshape(1, 1, 3)
        rgb = np.clip(rgb * t, 0, 1)
    bb2 = _bb_to_2d(bb, h, w)
    rgb = np.clip(rgb + bb2[:, :, np.newaxis] * float(cfg.get("bb_gain", 0.10)), 0, 1)
    m3 = mask[:, :, np.newaxis]
    bl = np.clip(pm * float(cfg.get("direct", 0.92)), 0, 1)
    out = paint[:, :, :3] * (1.0 - m3 * bl) + rgb * m3 * bl
    return np.clip(out, 0, 1).astype(np.float32)


def _pf_paint_cluster(paint, shape, mask, seed, pm, bb, cfg: dict) -> np.ndarray:
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2] if len(shape) >= 2 else paint.shape[:2]
    h, w = int(h), int(w)
    seed_off = int(cfg["seed_off"])
    work_cap = int(cfg.get("paint_work_cap", _PF_WORK_CAP))
    scales = tuple(cfg.get("paint_region_scales", (52, 84, 120, 168)))
    weights = tuple(cfg.get("paint_region_weights", (0.26, 0.28, 0.28, 0.18)))
    region01 = _region_field(h, w, int(seed), seed_off, scales, weights, work_cap)
    rgb_stops = cfg["rgb_stops"]
    rgb = _rgb_lerp_stops(region01, rgb_stops)
    micro = _hash01((h, w), seed + seed_off, 131)
    grain01 = _region_field(h, w, int(seed), seed_off + 181, [2, 3, 5], [0.34, 0.33, 0.33], work_cap)
    amp = float(cfg.get("cluster_micro_amp", 0.045))
    rgb = np.clip(
        rgb + (micro[..., np.newaxis] - 0.5) * amp + (grain01[..., np.newaxis] - 0.5) * amp * 0.65,
        0,
        1,
    ).astype(np.float32)
    if cfg.get("tint"):
        t = np.array(cfg["tint"], dtype=np.float32).reshape(1, 1, 3)
        rgb = np.clip(rgb * t, 0, 1)
    bb2 = _bb_to_2d(bb, h, w)
    rgb = np.clip(rgb + bb2[:, :, np.newaxis] * float(cfg.get("bb_gain", 0.08)), 0, 1)
    m3 = mask[:, :, np.newaxis]
    bl = np.clip(pm * float(cfg.get("direct", 0.92)), 0, 1)
    out = paint[:, :, :3] * (1.0 - m3 * bl) + rgb * m3 * bl
    return np.clip(out, 0, 1).astype(np.float32)


def _pf_micro_hsv_fast(h, w, seed, seed_off, work_cap, scales, weights, cfg):
    """SPB-PERF-2026-06-13: grain-preserving fast path for the **plain micro**
    (non-palette, non-flake) Prism Forge diffuse.

    The original computed ``region01``/``grain01`` at ``work_cap`` then *upsampled*
    them to the full canvas and ran ~10 float32 ops + HSV->RGB at full res. On a
    2048 plate that elementwise arithmetic is the dominant cost (~2s; 4x the 1024
    cost -- memory-bandwidth bound). Here the *smooth* hue/sat/val (the
    region01/grain01 terms, which the old code also derived from the same
    upsampled-from-``work_cap`` fields) are built natively at the work shape and
    upsampled **once each**. Because ``_pf_resize`` is INTER_LINEAR (a partition-of-
    unity weighted average) and these terms are affine in the fields,
    ``upsample(k*field_w + ...)`` == ``k*upsample(field_w) + ...`` -- i.e. bit-close
    to the original smooth contribution (only float rounding differs).

    The per-pixel ``micro`` hash dither (hue_jitter / sat_micro / val_micro) is the
    only *true* full-res grain, so it is added at full canvas resolution AFTER the
    upsample -- preserving the 1-3px speckle that defines the look. Verified
    bit-identical (SSIM 1.000000, max-delta 0.0) against the original on the
    raw deterministic gate. ``_pf_work_shape`` is a no-op at/below the cap, so
    small previews stay byte-identical.

    Returns (hue, sat, val) at full (h, w).
    """
    wh, ww = _pf_work_shape(h, w, work_cap)
    region_w = _region_field(wh, ww, int(seed), seed_off, scales, weights, None)
    grain_w = _region_field(wh, ww, int(seed), seed_off + 191, [2, 3, 4], [0.34, 0.33, 0.33], None)

    phg = float(cfg.get("paint_hue_gain", 0.085))
    span = float(cfg["hue_span"])
    hue_w = (region_w * 2.0 - 1.0) * (span * phg)
    hue_w = hue_w + (grain_w * 2.0 - 1.0) * (float(cfg.get("micro_hue_amp", 0.008)) * span)

    psg = float(cfg.get("paint_sat_gain", 0.82))
    sat_w = region_w * (float(cfg["sat1"] - cfg["sat0"]) * psg)
    sat_w = sat_w + (grain_w * 2.0 - 1.0) * float(cfg.get("paint_fine_sat", 0.022))

    pvg = float(cfg.get("paint_val_gain", 0.86))
    val_w = region_w * (float(cfg["v1"] - cfg["v0"]) * pvg)
    val_w = val_w + (grain_w * 2.0 - 1.0) * float(cfg.get("paint_fine_val", 0.028))

    if (wh, ww) != (h, w):
        hue_w = _pf_resize(hue_w, h, w)
        sat_w = _pf_resize(sat_w, h, w)
        val_w = _pf_resize(val_w, h, w)
    micro = _hash01((h, w), seed + seed_off, 101)

    hue = float(cfg["hue_c"]) + hue_w
    hue = hue + (micro * 2.0 - 1.0) * float(cfg.get("hue_jitter", 0.012))
    hue = np.mod(hue, 1.0).astype(np.float32)

    sat = float(cfg["sat0"]) + sat_w
    sat = sat + micro * float(cfg.get("sat_micro", 0.028))
    sat = np.clip(sat, 0, 1).astype(np.float32)

    val = float(cfg["v0"]) + val_w
    val = val + micro * float(cfg.get("val_micro", 0.022))
    val = np.clip(val, 0, 1).astype(np.float32)
    return hue, sat, val


def _pf_paint_micro(paint, shape, mask, seed, pm, bb, cfg: dict) -> np.ndarray:
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2] if len(shape) >= 2 else paint.shape[:2]
    h, w = int(h), int(w)
    seed_off = int(cfg["seed_off"])
    work_cap = int(cfg.get("paint_work_cap", _PF_WORK_CAP))
    scales = tuple(cfg.get("paint_region_scales", (3, 6, 11, 18, 30)))
    weights = tuple(cfg.get("paint_region_weights", (0.2, 0.24, 0.22, 0.18, 0.16)))

    flake = cfg.get("rgb_flake")
    flake_active = isinstance(flake, (list, tuple)) and len(flake) >= 3
    # SPB-PERF-2026-06-13: full-mask plain-micro renders (the common 2048 base path)
    # take the grain-preserving fast HSV builder above. Palette / flake / partial-
    # zone renders keep the original full-res path verbatim (bit-identical look).
    _pal = cfg.get("hue_palette")
    _pal_active = isinstance(_pal, (list, tuple)) and len(_pal) >= 2
    if (not flake_active) and (not _pal_active):
        _mask2 = np.asarray(mask, dtype=np.float32)
        if bool(np.all(_mask2 != 0)):
            hue, sat, val = _pf_micro_hsv_fast(h, w, seed, seed_off, work_cap, scales, weights, cfg)
            r, g, b = hsv_to_rgb_vec(hue, sat, val)
            rgb = np.stack([r, g, b], axis=2).astype(np.float32)
            if cfg.get("tint"):
                t = np.array(cfg["tint"], dtype=np.float32).reshape(1, 1, 3)
                rgb = np.clip(rgb * t, 0, 1)
            bb2 = _bb_to_2d(bb, h, w)
            rgb = np.clip(rgb + bb2[:, :, np.newaxis] * float(cfg.get("bb_gain", 0.10)), 0, 1)
            m3 = mask[:, :, np.newaxis]
            bl = np.clip(pm * float(cfg.get("direct", 0.92)), 0, 1)
            out = paint[:, :, :3] * (1.0 - m3 * bl) + rgb * m3 * bl
            return np.clip(out, 0, 1).astype(np.float32)
    # SPB-PERF-2026-06-04: the rgb_flake field carries the actual flake *grain*
    # (scale_sets reach 1-3px cells), so its resolution sets the look and must NOT
    # be capped below the existing work cap or the flake repositions/coarsens.
    # The *companion* fields it modulates with -- the per-pixel ``micro`` hash
    # dither (amp ~0.04), the ``grain01`` luminance pulse (amp ~0.05-0.11), and
    # the very-low-amp ``region01`` tilt (region_amp <=0.25, typically <=0.06) --
    # are low-amplitude and smooth; solving them at a tighter cap and resizing is
    # visually negligible (and a no-op at/below the cap, so 160/256px previews
    # stay byte-identical). Capping these trims cost without touching flake grain.
    # SPB-PERF-2026-06-04: the rgb_flake field carries the actual flake *grain*
    # (scale_sets reach 1-3px cells), so its resolution sets the look and must NOT
    # be capped below the existing work cap or the flake repositions/coarsens.
    # The *companion* fields it modulates with -- the per-pixel ``micro`` hash
    # dither (amp ~0.04), the ``grain01`` luminance pulse (amp ~0.05-0.11), and
    # the very-low-amp ``region01`` tilt (region_amp <=0.25, typically <=0.06) --
    # are low-amplitude and smooth; solving them at a tighter cap and resizing is
    # visually negligible (and a no-op at/below the cap, so 160/256px previews
    # stay byte-identical). Capping these trims cost without touching flake grain.
    comp_cap = int(cfg.get("paint_companion_cap", _PF_PAINT_CAP)) if flake_active else work_cap
    region01 = _region_field(h, w, int(seed), seed_off, scales, weights, comp_cap)
    if flake_active:
        micro = _hash01_capped(h, w, seed + seed_off, 101, comp_cap)
    else:
        micro = _hash01((h, w), seed + seed_off, 101)
    grain01 = _region_field(h, w, int(seed), seed_off + 191, [2, 3, 4], [0.34, 0.33, 0.33], comp_cap)

    if flake_active:
        sharp = float(cfg.get("rgb_flake_sharp", 8.5))
        fss = cfg.get("rgb_flake_scale_sets")
        if isinstance(fss, (list, tuple)) and len(fss) > 0:
            scale_sets = tuple(tuple(int(x) for x in row) for row in fss)
        else:
            scale_sets = None
        lhf = float(cfg.get("rgb_flake_logit_hf", 0.0))
        # flake field stays at the full work cap to preserve 1-3px flake grain.
        rgb = _rgb_flake_rgb(
            h, w, int(seed), seed_off, list(flake), sharp, scale_sets, lhf, work_cap
        )
        m_amp = float(cfg.get("rgb_flake_micro", 0.042))
        rgb = np.clip(rgb + (micro[..., np.newaxis] - 0.5) * m_amp, 0, 1)
        pulse = float(cfg.get("rgb_flake_lum_pulse", 0.14))
        rgb = np.clip(rgb * (1.0 + (grain01 - 0.5) * pulse)[..., np.newaxis], 0, 1)
        r_amp = float(cfg.get("rgb_flake_region_amp", 0.06))
        r_amp = float(np.clip(r_amp, 0.0, 0.25))
        rgb = np.clip(rgb * ((1.0 - r_amp) + r_amp * region01)[..., np.newaxis], 0, 1)
    else:
        pal = cfg.get("hue_palette")
        if isinstance(pal, (list, tuple)) and len(pal) >= 2:
            pj = float(cfg.get("hue_palette_jitter", 0.22))
            hue = _hue_walk_from_palette(region01, [float(x) for x in pal], micro, pj)
            phg = float(cfg.get("paint_hue_gain", 0.085))
            hue = hue + (grain01 * 2.0 - 1.0) * float(cfg.get("micro_hue_amp", 0.012)) * phg
            hue = np.mod(hue, 1.0).astype(np.float32)
        else:
            phg = float(cfg.get("paint_hue_gain", 0.085))
            hue = float(cfg["hue_c"]) + (region01 * 2.0 - 1.0) * float(cfg["hue_span"]) * phg
            hue = hue + (micro * 2.0 - 1.0) * float(cfg.get("hue_jitter", 0.012))
            hue = hue + (grain01 * 2.0 - 1.0) * float(cfg.get("micro_hue_amp", 0.008)) * float(cfg["hue_span"])
            hue = np.mod(hue, 1.0).astype(np.float32)

        psg = float(cfg.get("paint_sat_gain", 0.82))
        sat = float(cfg["sat0"]) + region01 * float(cfg["sat1"] - cfg["sat0"]) * psg
        sat = sat + (grain01 * 2.0 - 1.0) * float(cfg.get("paint_fine_sat", 0.022))
        sat = sat + micro * float(cfg.get("sat_micro", 0.028))
        sat = np.clip(sat, 0, 1).astype(np.float32)

        pvg = float(cfg.get("paint_val_gain", 0.86))
        val = float(cfg["v0"]) + region01 * float(cfg["v1"] - cfg["v0"]) * pvg
        val = val + (grain01 * 2.0 - 1.0) * float(cfg.get("paint_fine_val", 0.028))
        val = val + micro * float(cfg.get("val_micro", 0.022))
        val = np.clip(val, 0, 1).astype(np.float32)

        mask2 = np.asarray(mask, dtype=np.float32)
        active = mask2 != 0
        # SPB-PERF-2026-06-02: live truck renders often apply Prism Forge
        # parents to partial zone masks. Avoid converting hidden HSV pixels
        # to RGB; visible pixels get the same math, outside pixels stay paint.
        if np.any(active) and float(np.mean(active)) < 0.92:
            r, g, b = hsv_to_rgb_vec(hue[active], sat[active], val[active])
            rgb_active = np.stack([r, g, b], axis=1).astype(np.float32)
            if cfg.get("tint"):
                t = np.array(cfg["tint"], dtype=np.float32).reshape(1, 3)
                rgb_active = np.clip(rgb_active * t, 0, 1)
            bb_gain = float(cfg.get("bb_gain", 0.10))
            if abs(bb_gain) > 1e-8:
                bb_active = _bb_active_values(bb, h, w, active)
                rgb_active = np.clip(
                    rgb_active + np.asarray(bb_active, dtype=np.float32).reshape(-1, 1) * bb_gain,
                    0,
                    1,
                )
            out = paint[:, :, :3].copy()
            bl = np.clip(pm * float(cfg.get("direct", 0.92)), 0, 1)
            mix = (mask2[active] * bl)[:, np.newaxis]
            out[active] = out[active] * (1.0 - mix) + rgb_active * mix
            return np.clip(out, 0, 1).astype(np.float32)

        r, g, b = hsv_to_rgb_vec(hue, sat, val)
        rgb = np.stack([r, g, b], axis=2).astype(np.float32)
    if cfg.get("tint"):
        t = np.array(cfg["tint"], dtype=np.float32).reshape(1, 1, 3)
        rgb = np.clip(rgb * t, 0, 1)
    bb2 = _bb_to_2d(bb, h, w)
    rgb = np.clip(rgb + bb2[:, :, np.newaxis] * float(cfg.get("bb_gain", 0.10)), 0, 1)
    m3 = mask[:, :, np.newaxis]
    bl = np.clip(pm * float(cfg.get("direct", 0.92)), 0, 1)
    out = paint[:, :, :3] * (1.0 - m3 * bl) + rgb * m3 * bl
    return np.clip(out, 0, 1).astype(np.float32)


def _pf_paint(paint, shape, mask, seed, pm, bb, cfg: dict) -> np.ndarray:
    eng = str(cfg.get("engine", "micro_v3"))
    if eng == "legacy_v2":
        return _pf_paint_legacy(paint, shape, mask, seed, pm, bb, cfg)
    if eng == "cluster":
        return _pf_paint_cluster(paint, shape, mask, seed, pm, bb, cfg)
    return _pf_paint_micro(paint, shape, mask, seed, pm, bb, cfg)


def _pf_spec_legacy(shape, seed, sm, _base_m, _base_r, cfg: dict):
    h, w = shape[:2] if len(shape) >= 2 else shape
    h, w = int(h), int(w)
    seed_off = int(cfg["seed_off"])
    macro_style = str(cfg.get("macro_style", "flow"))
    macro = _macro_dispatch((h, w), int(seed), seed_off, macro_style)
    fine = _fine_spec_field(
        (h, w),
        int(seed),
        seed_off,
        float(cfg.get("spec_uf", 22.0)),
        float(cfg.get("spec_vf", 18.0)),
        float(cfg.get("spec_warp", 0.055)),
    )
    micro = _hash01((h, w), seed + seed_off, 311)
    sparkle = multi_scale_noise((h, w), [2, 4], [0.5, 0.5], seed + seed_off + 421)

    w_macro = float(cfg.get("spec_macro_weight", 0.42))
    w_fine = float(cfg.get("spec_fine_weight", 0.48))
    w_sp = float(cfg.get("spec_sparkle_weight", 0.28))
    mix = np.clip(
        macro * w_macro + fine * w_fine + micro * w_sp + sparkle * 0.12,
        0,
        1,
    ).astype(np.float32)

    ridge = np.clip(np.power(mix, float(cfg.get("ridge_gamma", 1.12))), 0, 1)
    glint = np.clip(
        ridge * float(cfg.get("ridge_to_glint", 0.58))
        + fine * float(cfg.get("fine_to_glint", 0.28))
        + micro * float(cfg.get("flake_gain", 0.22)),
        0,
        1,
    ).astype(np.float32)

    m_hi = float(cfg["m_hi"])
    m_lo = float(cfg["m_lo"])
    r_hi = float(cfg["r_hi"])
    r_lo = float(cfg["r_lo"])
    cc_hi = float(cfg["cc_hi"])
    cc_lo = float(cfg["cc_lo"])

    smf = float(np.clip(sm, 0.0, 1.0))
    M = m_lo + glint * (m_hi - m_lo) * smf + micro * float(cfg.get("m_micro", 26.0)) * smf
    R = r_lo - glint * (r_lo - r_hi) * smf + micro * float(cfg.get("r_micro", 11.0)) * smf
    CC = cc_lo - glint * (cc_lo - cc_hi) * smf + micro * float(cfg.get("cc_micro", 9.0)) * smf
    return (
        np.clip(M, 0, 255).astype(np.float32),
        np.clip(R, 15, 255).astype(np.float32),
        np.clip(CC, 16, 255).astype(np.float32),
    )


def _pf_spec_intrinsic(shape, seed, sm, _base_m, _base_r, cfg: dict):
    h, w = shape[:2] if len(shape) >= 2 else shape
    h, w = int(h), int(w)
    seed_off = int(cfg["seed_off"])
    work_cap = cfg.get("spec_work_cap", _PF_SPEC_CAP)
    # SPB perf loop 2026-05-31: Prism Forge spec is richly shaded but does not
    # need every carrier solved on the final canvas. Compute the M/R/CC field at
    # a bounded work size and resize back, preserving many spec shades while
    # keeping base renders under the owner's 4.000s hard ceiling.
    out_h, out_w = h, w
    h, w = _pf_work_shape(out_h, out_w, work_cap)
    ultra = _ultra_carrier((h, w), int(seed), seed_off, cfg)
    fine = _fine_spec_field(
        (h, w),
        int(seed),
        seed_off,
        float(cfg.get("spec_uf", 168.0)),
        float(cfg.get("spec_vf", 152.0)),
        float(cfg.get("spec_warp", 0.038)),
        work_cap,
    )
    micro = _hash01((h, w), seed + seed_off, 311)
    sparkle = _noise_field(h, w, int(seed), seed_off + 421, [2, 3, 5], [0.34, 0.33, 0.33], work_cap)

    w_u = float(cfg.get("spec_ultra_weight", 0.50))
    w_f = float(cfg.get("spec_fine_weight", 0.40))
    w_sp = float(cfg.get("spec_sparkle_weight", 0.26))
    mix = np.clip(
        ultra * w_u + fine * w_f + micro * w_sp + sparkle * 0.11,
        0,
        1,
    ).astype(np.float32)

    ridge = np.clip(np.power(mix, float(cfg.get("ridge_gamma", 1.12))), 0, 1)
    glint = np.clip(
        ridge * float(cfg.get("ridge_to_glint", 0.62))
        + fine * float(cfg.get("fine_to_glint", 0.30))
        + micro * float(cfg.get("flake_gain", 0.22)),
        0,
        1,
    ).astype(np.float32)

    m_hi = float(cfg["m_hi"])
    m_lo = float(cfg["m_lo"])
    r_hi = float(cfg["r_hi"])
    r_lo = float(cfg["r_lo"])
    cc_hi = float(cfg["cc_hi"])
    cc_lo = float(cfg["cc_lo"])

    smf = float(np.clip(sm, 0.0, 1.0))
    M = m_lo + glint * (m_hi - m_lo) * smf + micro * float(cfg.get("m_micro", 26.0)) * smf
    R = r_lo - glint * (r_lo - r_hi) * smf + micro * float(cfg.get("r_micro", 11.0)) * smf
    CC = cc_lo - glint * (cc_lo - cc_hi) * smf + micro * float(cfg.get("cc_micro", 9.0)) * smf
    return (
        _pf_resize(np.clip(M, 0, 255).astype(np.float32), out_h, out_w),
        _pf_resize(np.clip(R, 15, 255).astype(np.float32), out_h, out_w),
        _pf_resize(np.clip(CC, 16, 255).astype(np.float32), out_h, out_w),
    )


def _pf_spec_depth3d(shape, seed, sm, _base_m, _base_r, cfg: dict):
    """v4 — DEPTH/3D/MOTION spec that TRACES the paint's own geometry.

    The v3 intrinsic spec built ultra/fine carriers in their OWN UV space, so the
    spec glints never landed on the painted design (it read flat / wallpapered).
    v4 reconstructs the SAME seeded ``region01``/``grain01`` fields the paint colors
    with (identical seed + scales), treats that painted value structure as a HEIGHT
    field, and runs it through ``depth3d_2026.compose_depth_spec`` — giving the spec:

      * fake-3D bevel relief (height->normals->Lambert) so the flat livery catches
        the moving iRacing sun like it has sculpted depth,
      * an edge-catch rim glint exactly on the paint's region boundaries,
      * a phase-set traveling color/glint shift (the "moving" read),
      * three decorrelated M/R/Cc geometries (|corr| < 0.85 falls out of the lib).

    The library's decorrelated output is then remapped into THIS finish's own
    ``m/r/cc`` envelope and scaled by ``sm`` (same convention as the legacy path:
    sm=0 -> calm baseline, sm=1 -> full excursion) so each finish keeps its identity.
    """
    from engine.paint_v2 import depth3d_2026 as _d3

    h, w = shape[:2] if len(shape) >= 2 else shape
    out_h, out_w = int(h), int(w)
    seed_off = int(cfg["seed_off"])
    work_cap = cfg.get("spec_work_cap", _PF_SPEC_CAP)
    wh, ww = _pf_work_shape(out_h, out_w, work_cap)

    # --- reconstruct the PAINT design luma (same seed/scales the paint colors with) ---
    # The spec must trace the SAME geometry the paint draws, so the height field is built
    # from whichever engine the row's paint uses:
    #   * rgb_flake  -> the multi-primary flake luma (its softmax cells ARE the design),
    #   * hue/palette/cluster -> the region value structure (region01 drives those).
    eng = str(cfg.get("engine", "micro_v3"))
    if eng == "cluster":
        scales = tuple(cfg.get("paint_region_scales", (52, 84, 120, 168)))
        weights = tuple(cfg.get("paint_region_weights", (0.26, 0.28, 0.28, 0.18)))
    else:
        scales = tuple(cfg.get("paint_region_scales", (3, 6, 11, 18, 30)))
        weights = tuple(cfg.get("paint_region_weights", (0.2, 0.24, 0.22, 0.18, 0.16)))
    region01 = _region_field(wh, ww, int(seed), seed_off, scales, weights, work_cap)
    grain01 = _region_field(wh, ww, int(seed), seed_off + 191, [2, 3, 4],
                            [0.34, 0.33, 0.33], work_cap)

    flake = cfg.get("rgb_flake")
    if isinstance(flake, (list, tuple)) and len(flake) >= 3:
        sharp = float(cfg.get("rgb_flake_sharp", 8.5))
        fss = cfg.get("rgb_flake_scale_sets")
        scale_sets = (tuple(tuple(int(x) for x in row) for row in fss)
                      if isinstance(fss, (list, tuple)) and len(fss) > 0 else None)
        lhf = float(cfg.get("rgb_flake_logit_hf", 0.0))
        rgbf = _rgb_flake_rgb(wh, ww, int(seed), seed_off, list(flake), sharp,
                              scale_sets, lhf, work_cap)
        flake_luma = (0.2126 * rgbf[:, :, 0] + 0.7152 * rgbf[:, :, 1]
                      + 0.0722 * rgbf[:, :, 2]).astype(np.float32)
        # blend a touch of region tilt so the relief also follows the macro blend pockets
        paint_luma = np.clip(0.82 * flake_luma + 0.18 * region01, 0.0, 1.0).astype(np.float32)
    elif eng == "cluster" and cfg.get("rgb_stops"):
        # cluster paint = rgb_lerp over region01; its luma IS the design relief.
        rgbc = _rgb_lerp_stops(region01, cfg["rgb_stops"])
        paint_luma = np.clip(
            0.2126 * rgbc[:, :, 0] + 0.7152 * rgbc[:, :, 1] + 0.0722 * rgbc[:, :, 2],
            0.0, 1.0).astype(np.float32)
    else:
        # micro_v3 hue-drift / hue_palette: value structure follows region01.
        pvg = float(cfg.get("paint_val_gain", 0.86))
        v0 = float(cfg.get("v0", 0.08)); v1 = float(cfg.get("v1", 0.42))
        paint_luma = np.clip(
            v0 + region01 * (v1 - v0) * pvg
            + (grain01 * 2.0 - 1.0) * float(cfg.get("paint_fine_val", 0.028)),
            0.0, 1.0).astype(np.float32)

    # --- DEPTH / FAKE-3D that TRACES the paint topology (solved at work res) ---
    # Two sun angles off the SAME height field give M and Cc independent relief reads
    # (decorrelation via different aspects of one motif, not alien geometry); the edge
    # catch is the machined-rim glint; the traveling shift is the in-sim "moving" read.
    relief = float(cfg.get("spec_relief", 2.4))
    lightA = tuple(cfg.get("spec_light_dir", (0.55, 0.42, 0.72)))
    lightB = tuple(cfg.get("spec_light_dir_b", (-0.46, -0.38, 0.74)))
    nrm = _d3.height_to_normals(paint_luma, strength=relief)
    bevelA = _d3.shade_bevels(nrm, light_dir=lightA, ambient=0.12, gamma=1.12)
    bevelB = _d3.shade_bevels(nrm, light_dir=lightB, ambient=0.16, gamma=0.92)
    edge = _d3.bevel_edge_catch(paint_luma, blur=0.8, gamma=0.7)
    phase = float(cfg.get("spec_phase", (seed_off % 19) * 0.331))
    bands = float(cfg.get("spec_bands", 7.0))
    motionM = _d3.traveling_colorshift(paint_luma, phase, bands=bands, sharpness=2.2)
    motionC = _d3.traveling_colorshift(paint_luma, phase + 2.1, bands=bands * 0.7,
                                       sharpness=1.8, direction=(0.35, 1.0))

    # --- FINE sparkle / flake grain (carries the fineness + metal-flake glint) ---
    # Solved at the same work res as the depth fields; the final M/R/Cc are resized to
    # the canvas ONCE. Computing the HF carriers at the work cap (then resizing 3.2x to
    # 2048) keeps the spec ~as cheap as the old intrinsic path while leaving huge
    # fineness headroom, and lands flake grain at the 2-3px scale that reads as metal
    # rather than 1px digital noise. The sparkle is modulated by the traced relief so it
    # sits ON the painted topology instead of floating as alien noise.
    ultra = _ultra_carrier((wh, ww), int(seed), seed_off, cfg)
    micro = _hash01((wh, ww), seed + seed_off, 311)
    grain_hf = _hash01((wh, ww), seed + seed_off, 733)
    sparkle = np.clip(ultra * 0.55 + micro * 0.45, 0, 1).astype(np.float32)
    sparkle = sparkle * (0.40 + 0.60 * bevelA)

    def _n(a):
        a = a.astype(np.float32)
        lo = float(a.min()); rng = float(np.ptp(a))
        return np.zeros_like(a) if rng < 1e-6 else (a - lo) / rng

    # paint design VALUE itself so the metal lives IN the design, not just on its edges:
    # brighter painted regions pool more metallic, darker read rougher.
    design_w = _n(paint_luma)
    tv = float(cfg.get("spec_value_trace", 0.32))

    # --- three decorrelated GLOSS fields, each a different aspect + its own HF ---
    gM = _n(np.clip(0.60 * bevelA + 0.20 * edge + 0.26 * motionM + 0.44 * sparkle
                    + tv * design_w, 0, 1))
    gRg = _n(np.clip(0.50 * edge + 0.55 * grain_hf + 0.12 * bevelA
                     + tv * (1.0 - design_w), 0, 1))
    gCc = _n(np.clip(0.62 * bevelB + 0.24 * motionC + 0.20 * sparkle
                     + 0.18 * micro, 0, 1))

    m_hi = float(cfg["m_hi"]); m_lo = float(cfg["m_lo"])
    r_hi = float(cfg["r_hi"]); r_lo = float(cfg["r_lo"])
    cc_hi = float(cfg["cc_hi"]); cc_lo = float(cfg["cc_lo"])

    # Map each gloss field into this finish's envelope; excursion scaled by sm around
    # the calm baseline (lo). Roughness/Clearcoat go toward their glossy hi as gloss
    # rises (r_hi/cc_hi are the low/glossy ends per SPB channel polarity).
    smf = float(np.clip(sm, 0.0, 1.0))
    M = m_lo + (gM * (m_hi - m_lo)) * smf
    R = r_lo + (gRg * (r_hi - r_lo)) * smf
    CC = cc_lo + (gCc * (cc_hi - cc_lo)) * smf

    return (
        _pf_resize(np.clip(M, 0, 255).astype(np.float32), out_h, out_w),
        _pf_resize(np.clip(R, 15, 255).astype(np.float32), out_h, out_w),
        _pf_resize(np.clip(CC, 16, 255).astype(np.float32), out_h, out_w),
    )


def _pf_spec(shape, seed, sm, _base_m, _base_r, cfg: dict):
    # legacy_v2 finishes (Void Pearl / Copper Moon) keep their artist-locked PAINT, but
    # their v2 spec drove M/R/Cc from one field (|corr| ~0.93-0.94, fails the <0.85 gate).
    # 2026-06-20: decorrelate + add bevel relief to the legacy spec only (paint untouched).
    if str(cfg.get("engine", "micro_v3")) == "legacy_v2":
        _M, _R, _CC = _pf_spec_legacy(shape, seed, sm, _base_m, _base_r, cfg)
        from engine.paint_v2 import depth3d_2026 as _d3
        return _d3.decorrelate_envelope(_M, _R, _CC,
                                        seed=int(seed) + int(cfg.get("seed_off", 0)), blend=0.6)
    # 2026-06-20 PRISM FORGE rework: DEPTH/3D/MOTION spec that TRACES the paint is now
    # the default for every non-legacy finish. A row may opt back to the old flat
    # carrier spec with spec_engine="intrinsic" (none currently do).
    if str(cfg.get("spec_engine", "depth3d")) == "intrinsic":
        return _pf_spec_intrinsic(shape, seed, sm, _base_m, _base_r, cfg)
    return _pf_spec_depth3d(shape, seed, sm, _base_m, _base_r, cfg)


def _row(**kwargs) -> dict:
    return kwargs


_PF_ROWS = (
    _row(
        id="pf_event_horizon_spectra",
        seed_off=9600,
        spec_engine="depth3d",
        hue_c=0.78,
        hue_span=0.52,
        paint_hue_gain=0.072,
        paint_region_scales=(3, 6, 12, 22, 38),
        sat0=0.22,
        sat1=0.68,
        v0=0.05,
        v1=0.34,
        spec_uf=178,
        spec_vf=156,
        spec_warp=0.034,
        spec_cycles_x=668,
        spec_cycles_y=601,
        spec_cycles_diag=547,
        m_hi=242,
        m_lo=20,
        r_hi=15,
        r_lo=132,
        cc_hi=18,
        cc_lo=82,
        desc="PRISM FORGE Event Horizon Spectra — v3: ink-quiet diffuse; sub-pixel spec carriers stack spectral flash in sim.",
    ),
    _row(
        id="pf_chromatic_storm",
        seed_off=9601,
        spec_engine="depth3d",
        hue_c=0.52,
        hue_span=0.58,
        paint_hue_gain=0.088,
        paint_region_scales=(3, 7, 14, 26, 40),
        sat0=0.36,
        sat1=0.82,
        v0=0.10,
        v1=0.46,
        spec_uf=186,
        spec_vf=162,
        spec_warp=0.036,
        spec_cycles_x=702,
        spec_cycles_y=589,
        spec_cycles_diag=521,
        tri_power=0.40,
        m_hi=244,
        m_lo=26,
        r_hi=15,
        r_lo=118,
        cc_hi=18,
        cc_lo=70,
        desc="PRISM FORGE Chromatic Storm — v3: crushed multi-scale hue fog + dense spec interference (no damascus wallpaper).",
    ),
    _row(
        id="pf_neon_nova",
        seed_off=9602,
        spec_engine="depth3d",
        hue_c=0.90,
        hue_span=0.32,
        paint_hue_gain=0.095,
        paint_region_scales=(3, 6, 13, 24, 36),
        sat0=0.52,
        sat1=0.94,
        v0=0.09,
        v1=0.48,
        spec_uf=172,
        spec_vf=168,
        spec_warp=0.032,
        spec_cycles_x=640,
        spec_cycles_y=618,
        spec_cycles_diag=555,
        tint=(1.04, 0.96, 1.06),
        m_hi=246,
        m_lo=32,
        r_hi=15,
        r_lo=104,
        cc_hi=18,
        cc_lo=60,
        desc="PRISM FORGE Neon Nova — v3: no radial fan; pocket hue via micro regions + cyber-dense spec lattice.",
    ),
    _row(
        id="pf_molten_aurora",
        seed_off=9603,
        hue_c=0.04,
        hue_span=0.42,
        paint_hue_gain=0.082,
        paint_region_scales=(3, 7, 15, 28, 44),
        sat0=0.46,
        sat1=0.90,
        v0=0.08,
        v1=0.48,
        spec_uf=182,
        spec_vf=154,
        spec_warp=0.036,
        spec_cycles_x=655,
        spec_cycles_y=612,
        spec_cycles_diag=538,
        m_hi=238,
        m_lo=34,
        r_hi=15,
        r_lo=114,
        cc_hi=19,
        cc_lo=72,
        desc="PRISM FORGE Molten Aurora — v3: ember/teal without diagonal macro bands; heat reads from spec beats.",
    ),
    _row(
        id="pf_void_pearl",
        seed_off=9604,
        engine="legacy_v2",
        macro_style="flow",
        hue_c=0.74,
        hue_span=0.28,
        paint_hue_gain=0.07,
        paint_fine_val=0.03,
        sat0=0.12,
        sat1=0.48,
        v0=0.06,
        v1=0.34,
        spec_uf=52,
        spec_vf=40,
        spec_warp=0.05,
        m_hi=232,
        m_lo=48,
        r_hi=16,
        r_lo=92,
        cc_hi=22,
        cc_lo=52,
        ridge_gamma=1.38,
        spec_fine_weight=0.55,
        desc="PRISM FORGE Void Pearl — **unchanged v2 path** (artist hold); charcoal opal, spec-led bloom.",
    ),
    _row(
        id="pf_ion_trap",
        seed_off=9605,
        hue_c=0.58,
        hue_span=0.36,
        paint_hue_gain=0.078,
        paint_region_scales=(3, 6, 12, 20, 34),
        sat0=0.38,
        sat1=0.86,
        v0=0.10,
        v1=0.48,
        spec_uf=190,
        spec_vf=174,
        spec_warp=0.033,
        spec_cycles_x=688,
        spec_cycles_y=571,
        spec_cycles_diag=529,
        m_hi=242,
        m_lo=30,
        r_hi=15,
        r_lo=122,
        cc_hi=18,
        cc_lo=68,
        desc="PRISM FORGE Ion Trap — v3: electric blue-violet micro grain; no wide ion stripes in diffuse.",
    ),
    _row(
        id="pf_sapphire_blood",
        seed_off=9606,
        hue_c=0.62,
        hue_span=0.30,
        paint_hue_gain=0.076,
        paint_region_scales=(3, 7, 14, 24, 40),
        sat0=0.40,
        sat1=0.84,
        v0=0.07,
        v1=0.40,
        spec_uf=180,
        spec_vf=158,
        spec_warp=0.034,
        spec_cycles_x=672,
        spec_cycles_y=605,
        spec_cycles_diag=533,
        tint=(0.92, 0.98, 1.10),
        m_hi=236,
        m_lo=36,
        r_hi=15,
        r_lo=116,
        cc_hi=19,
        cc_lo=70,
        desc="PRISM FORGE Sapphire Blood — v3: jewel hue crushed to fine texture; wine undertow in spec mix.",
    ),
    _row(
        id="pf_emerald_inferno",
        seed_off=9607,
        hue_c=0.30,
        hue_span=0.34,
        paint_hue_gain=0.084,
        paint_region_scales=(3, 6, 13, 22, 38),
        sat0=0.46,
        sat1=0.92,
        v0=0.07,
        v1=0.46,
        spec_uf=176,
        spec_vf=170,
        spec_warp=0.035,
        spec_cycles_x=658,
        spec_cycles_y=624,
        spec_cycles_diag=548,
        tint=(0.92, 1.08, 0.94),
        m_hi=240,
        m_lo=28,
        r_hi=15,
        r_lo=120,
        cc_hi=18,
        cc_lo=72,
        desc="PRISM FORGE Emerald Inferno — v3: no pinwheel; acid/ember via micro hue + HF spec shards.",
    ),
    _row(
        id="pf_violet_sunrise",
        seed_off=9608,
        hue_c=0.78,
        hue_span=0.26,
        paint_hue_gain=0.068,
        paint_region_scales=(3, 6, 11, 19, 32),
        sat0=0.30,
        sat1=0.74,
        v0=0.12,
        v1=0.50,
        spec_uf=184,
        spec_vf=150,
        spec_warp=0.030,
        spec_cycles_x=645,
        spec_cycles_y=598,
        spec_cycles_diag=562,
        m_hi=228,
        m_lo=42,
        r_hi=16,
        r_lo=98,
        cc_hi=21,
        cc_lo=58,
        desc="PRISM FORGE Violet Sunrise — v3: dawn gold/violet as crushed fields; zero candy stripes.",
    ),
    _row(
        id="pf_copper_moon",
        seed_off=9609,
        engine="legacy_v2",
        macro_style="flow",
        hue_c=0.05,
        hue_span=0.22,
        paint_hue_gain=0.11,
        sat0=0.28,
        sat1=0.68,
        v0=0.14,
        v1=0.50,
        spec_uf=28,
        spec_vf=22,
        spec_warp=0.055,
        m_hi=218,
        m_lo=52,
        r_hi=17,
        r_lo=86,
        cc_hi=24,
        cc_lo=54,
        tint=(1.10, 0.90, 0.74),
        desc="PRISM FORGE Copper Moon — **unchanged v2 path** (artist hold); burnished copper, spec-led story.",
    ),
    _row(
        id="pf_toxic_horizon",
        seed_off=9610,
        hue_c=0.24,
        hue_span=0.40,
        paint_hue_gain=0.092,
        paint_region_scales=(3, 7, 15, 26, 42),
        sat0=0.50,
        sat1=0.96,
        v0=0.09,
        v1=0.50,
        spec_uf=188,
        spec_vf=166,
        spec_warp=0.037,
        spec_cycles_x=710,
        spec_cycles_y=582,
        spec_cycles_diag=515,
        tint=(0.92, 1.10, 0.90),
        m_hi=244,
        m_lo=30,
        r_hi=15,
        r_lo=108,
        cc_hi=18,
        cc_lo=64,
        desc="PRISM FORGE Toxic Horizon — v3: chartreuse/purple as micro mosaic; hazard glitter in spec.",
    ),
    _row(
        id="pf_glacial_burn",
        seed_off=9611,
        hue_c=0.52,
        hue_span=0.32,
        paint_hue_gain=0.070,
        paint_region_scales=(3, 6, 12, 21, 36),
        sat0=0.20,
        sat1=0.70,
        v0=0.16,
        v1=0.52,
        spec_uf=168,
        spec_vf=164,
        spec_warp=0.032,
        spec_cycles_x=628,
        spec_cycles_y=590,
        spec_cycles_diag=556,
        tri_power=0.50,
        spec_ultra_weight=0.46,
        spec_fine_weight=0.44,
        tint=(0.90, 1.04, 1.08),
        m_hi=232,
        m_lo=40,
        r_hi=16,
        r_lo=100,
        cc_hi=22,
        cc_lo=58,
        desc="PRISM FORGE Glacial Burn — v3: cooler, smoother ultra carrier vs Oil Nebula; ice/ember separation.",
    ),
    _row(
        id="pf_oil_nebula",
        seed_off=9612,
        hue_c=0.72,
        hue_span=0.52,
        paint_hue_gain=0.095,
        paint_region_scales=(3, 5, 10, 18, 32),
        sat0=0.36,
        sat1=0.86,
        v0=0.05,
        v1=0.38,
        spec_uf=194,
        spec_vf=148,
        spec_warp=0.041,
        spec_cycles_x=734,
        spec_cycles_y=563,
        spec_cycles_diag=489,
        tri_power=0.36,
        spec_ultra_warp=0.018,
        spec_ultra_weight=0.54,
        spec_fine_weight=0.36,
        m_hi=240,
        m_lo=22,
        r_hi=15,
        r_lo=128,
        cc_hi=18,
        cc_lo=78,
        desc="PRISM FORGE Oil Nebula — v3: distinct HF phase set from Glacial; thinner tri power, more warp chaos.",
    ),
    _row(
        id="pf_rose_quantum",
        seed_off=9613,
        hue_c=0.94,
        hue_span=0.24,
        paint_hue_gain=0.066,
        paint_region_scales=(3, 6, 11, 20, 34),
        sat0=0.33,
        sat1=0.76,
        v0=0.13,
        v1=0.46,
        spec_uf=170,
        spec_vf=160,
        spec_warp=0.031,
        spec_cycles_x=652,
        spec_cycles_y=608,
        spec_cycles_diag=540,
        tint=(1.08, 0.88, 0.96),
        m_hi=224,
        m_lo=46,
        r_hi=16,
        r_lo=92,
        cc_hi=22,
        cc_lo=54,
        desc="PRISM FORGE Rose Quantum — v3: no quantum pinwheel; rose/teal as micro pockets + jewelry spec.",
    ),
    _row(
        id="pf_cobalt_fire",
        seed_off=9614,
        hue_c=0.58,
        hue_span=0.34,
        paint_hue_gain=0.080,
        paint_region_scales=(3, 7, 14, 25, 40),
        sat0=0.46,
        sat1=0.92,
        v0=0.08,
        v1=0.48,
        spec_uf=182,
        spec_vf=172,
        spec_warp=0.034,
        spec_cycles_x=676,
        spec_cycles_y=596,
        spec_cycles_diag=528,
        tint=(0.90, 0.96, 1.12),
        m_hi=242,
        m_lo=32,
        r_hi=15,
        r_lo=114,
        cc_hi=18,
        cc_lo=68,
        desc="PRISM FORGE Cobalt Fire — v3: cobalt/lava without candy bands; flash is spec-led.",
    ),
    _row(
        id="pf_midnight_prism",
        seed_off=9615,
        hue_c=0.70,
        hue_span=0.40,
        paint_hue_gain=0.048,
        paint_region_scales=(2, 5, 9, 16, 28),
        micro_hue_amp=0.005,
        sat0=0.20,
        sat1=0.52,
        v0=0.03,
        v1=0.28,
        spec_uf=198,
        spec_vf=188,
        spec_warp=0.036,
        spec_cycles_x=692,
        spec_cycles_y=618,
        spec_cycles_diag=552,
        spec_fine_weight=0.52,
        ridge_gamma=1.22,
        m_hi=244,
        m_lo=22,
        r_hi=15,
        r_lo=130,
        cc_hi=18,
        cc_lo=80,
        desc="PRISM FORGE Midnight Prism — v3: ink-quiet plane; prismatic lightning almost entirely in spec.",
    ),
    _row(
        id="pf_hyperwave",
        seed_off=9616,
        hue_c=0.48,
        hue_span=0.44,
        paint_hue_gain=0.086,
        paint_region_scales=(3, 6, 13, 24, 38),
        sat0=0.40,
        sat1=0.90,
        v0=0.10,
        v1=0.52,
        spec_uf=186,
        spec_vf=158,
        spec_warp=0.033,
        spec_cycles_x=704,
        spec_cycles_y=579,
        spec_cycles_diag=521,
        m_hi=242,
        m_lo=28,
        r_hi=15,
        r_lo=118,
        cc_hi=18,
        cc_lo=66,
        desc="PRISM FORGE Hyperwave — v3: lateral energy without macro sweep stripes; HF spec scan texture.",
    ),
    _row(
        id="pf_crystal_fade",
        seed_off=9617,
        hue_c=0.52,
        hue_span=0.16,
        paint_hue_gain=0.055,
        paint_region_scales=(3, 6, 10, 18, 30),
        sat0=0.10,
        sat1=0.48,
        v0=0.20,
        v1=0.56,
        spec_uf=174,
        spec_vf=176,
        spec_warp=0.028,
        spec_cycles_x=618,
        spec_cycles_y=602,
        spec_cycles_diag=568,
        ridge_gamma=1.48,
        m_hi=210,
        m_lo=58,
        r_hi=18,
        r_lo=78,
        cc_hi=26,
        cc_lo=48,
        desc="PRISM FORGE Crystal Fade — v3: opal milk micro veins + satin frost spec (tighter than v2 wallpaper).",
    ),
    _row(
        id="pf_dark_matter_halo",
        seed_off=9618,
        hue_c=0.76,
        hue_span=0.26,
        paint_hue_gain=0.052,
        paint_region_scales=(3, 5, 10, 17, 30),
        sat0=0.16,
        sat1=0.52,
        v0=0.02,
        v1=0.26,
        spec_uf=192,
        spec_vf=170,
        spec_warp=0.034,
        spec_cycles_x=682,
        spec_cycles_y=611,
        spec_cycles_diag=535,
        m_hi=238,
        m_lo=26,
        r_hi=15,
        r_lo=124,
        cc_hi=20,
        cc_lo=74,
        desc="PRISM FORGE Dark Matter Halo — v3: void base; halo is HF spec ridge energy, not radial pinwheel paint.",
    ),
    _row(
        id="pf_apex_spectrum",
        seed_off=9619,
        hue_c=0.14,
        hue_span=0.50,
        paint_hue_gain=0.090,
        paint_region_scales=(3, 6, 12, 22, 36),
        sat0=0.44,
        sat1=0.96,
        v0=0.08,
        v1=0.52,
        spec_uf=200,
        spec_vf=182,
        spec_warp=0.038,
        spec_cycles_x=718,
        spec_cycles_y=566,
        spec_cycles_diag=498,
        spec_ultra_weight=0.52,
        m_hi=248,
        m_lo=22,
        r_hi=15,
        r_lo=126,
        cc_hi=18,
        cc_lo=76,
        desc="PRISM FORGE Apex Spectrum — v3: max hue walk still **micro** on albedo; bold metallic in spec (no cell wallpaper).",
    ),
    _row(
        id="pf_cluster_tar_eclipse",
        seed_off=9620,
        engine="cluster",
        rgb_stops=[
            (0.02, 0.02, 0.03),
            (0.12, 0.08, 0.14),
            (0.55, 0.42, 0.12),
            (0.35, 0.12, 0.42),
            (0.10, 0.22, 0.38),
            (0.03, 0.03, 0.04),
        ],
        paint_region_scales=(48, 76, 112, 164),
        cluster_micro_amp=0.042,
        spec_uf=182,
        spec_vf=168,
        spec_warp=0.035,
        spec_cycles_x=660,
        spec_cycles_y=604,
        spec_cycles_diag=528,
        m_hi=236,
        m_lo=34,
        r_hi=15,
        r_lo=118,
        cc_hi=19,
        cc_lo=70,
        desc="PRISM FORGE Cluster Tar Eclipse — black islands: gold/violet/teal pockets + crushed grain.",
    ),
    _row(
        id="pf_cluster_bitumen_aurora",
        seed_off=9621,
        engine="cluster",
        rgb_stops=[
            (0.03, 0.03, 0.04),
            (0.08, 0.14, 0.12),
            (0.42, 0.55, 0.18),
            (0.22, 0.10, 0.36),
            (0.14, 0.28, 0.52),
            (0.02, 0.02, 0.03),
        ],
        paint_region_scales=(52, 88, 128, 176),
        paint_region_weights=(0.22, 0.28, 0.28, 0.22),
        cluster_micro_amp=0.048,
        spec_uf=188,
        spec_vf=160,
        spec_warp=0.036,
        spec_cycles_x=688,
        spec_cycles_y=592,
        spec_cycles_diag=512,
        tri_power=0.38,
        m_hi=238,
        m_lo=30,
        r_hi=15,
        r_lo=122,
        cc_hi=18,
        cc_lo=72,
        desc="PRISM FORGE Cluster Bitumen Aurora — tar-black with scattered aurora RGB pockets; unique island layout.",
    ),
    _row(
        id="pf_cluster_obsidian_gild",
        seed_off=9622,
        engine="cluster",
        rgb_stops=[
            (0.02, 0.02, 0.02),
            (0.45, 0.32, 0.10),
            (0.52, 0.48, 0.12),
            (0.18, 0.14, 0.42),
            (0.10, 0.26, 0.22),
            (0.03, 0.03, 0.04),
        ],
        paint_region_scales=(56, 92, 132, 188),
        cluster_micro_amp=0.040,
        spec_uf=176,
        spec_vf=174,
        spec_warp=0.033,
        spec_cycles_x=648,
        spec_cycles_y=618,
        spec_cycles_diag=544,
        m_hi=232,
        m_lo=38,
        r_hi=16,
        r_lo=108,
        cc_hi=20,
        cc_lo=64,
        desc="PRISM FORGE Cluster Obsidian Gild — gilded micro-pools on obsidian; purple/teal counter-islands.",
    ),
    _row(
        id="pf_cluster_coal_starfield",
        seed_off=9623,
        engine="cluster",
        rgb_stops=[
            (0.02, 0.02, 0.03),
            (0.22, 0.20, 0.24),
            (0.42, 0.12, 0.50),
            (0.12, 0.38, 0.52),
            (0.48, 0.36, 0.14),
            (0.02, 0.02, 0.03),
        ],
        paint_region_scales=(44, 72, 108, 156),
        cluster_micro_amp=0.052,
        spec_uf=194,
        spec_vf=152,
        spec_warp=0.037,
        spec_cycles_x=712,
        spec_cycles_y=578,
        spec_cycles_diag=505,
        m_hi=242,
        m_lo=26,
        r_hi=15,
        r_lo=124,
        cc_hi=18,
        cc_lo=74,
        desc="PRISM FORGE Cluster Coal Starfield — coal black with starfield jewel pockets; denser micro sparkle.",
    ),
    _row(
        id="pf_cluster_void_islands",
        seed_off=9624,
        engine="cluster",
        rgb_stops=[
            (0.02, 0.02, 0.04),
            (0.30, 0.10, 0.42),
            (0.12, 0.32, 0.48),
            (0.48, 0.22, 0.12),
            (0.20, 0.42, 0.22),
            (0.03, 0.03, 0.05),
        ],
        paint_region_scales=(60, 96, 140, 196),
        paint_region_weights=(0.24, 0.26, 0.26, 0.24),
        cluster_micro_amp=0.046,
        spec_uf=186,
        spec_vf=166,
        spec_warp=0.034,
        spec_cycles_x=672,
        spec_cycles_y=600,
        spec_cycles_diag=532,
        m_hi=240,
        m_lo=28,
        r_hi=15,
        r_lo=120,
        cc_hi=19,
        cc_lo=68,
        desc="PRISM FORGE Cluster Void Islands — void black + isolated hue archipelagos; each island unique weighting.",
    ),
    _row(
        id="pf_bright_solar_daffodil",
        seed_off=9625,
        hue_c=0.14,
        hue_span=0.18,
        paint_hue_gain=0.10,
        paint_region_scales=(3, 6, 12, 22, 36),
        sat0=0.62,
        sat1=0.96,
        v0=0.62,
        v1=0.92,
        spec_uf=178,
        spec_vf=170,
        spec_warp=0.032,
        spec_cycles_x=652,
        spec_cycles_y=610,
        spec_cycles_diag=548,
        tint=(1.08, 1.06, 0.88),
        m_hi=236,
        m_lo=40,
        r_hi=16,
        r_lo=102,
        cc_hi=22,
        cc_lo=62,
        desc="PRISM FORGE Bright Solar Daffodil — high-key yellow sun plate; micro hue so sponsors stay clean.",
    ),
    _row(
        id="pf_bright_hyperpink",
        seed_off=9626,
        hue_c=0.92,
        hue_span=0.14,
        paint_hue_gain=0.11,
        paint_region_scales=(3, 6, 11, 20, 34),
        sat0=0.70,
        sat1=0.99,
        v0=0.58,
        v1=0.90,
        spec_uf=184,
        spec_vf=162,
        spec_warp=0.031,
        spec_cycles_x=668,
        spec_cycles_y=594,
        spec_cycles_diag=536,
        tint=(1.12, 0.90, 1.05),
        m_hi=240,
        m_lo=34,
        r_hi=15,
        r_lo=108,
        cc_hi=20,
        cc_lo=64,
        desc="PRISM FORGE Bright Hyperpink — neon magenta/pink pop with crushed micro texture + glass spec.",
    ),
    _row(
        id="pf_bright_seafoam_bolt",
        seed_off=9627,
        hue_c=0.48,
        hue_span=0.22,
        paint_hue_gain=0.10,
        paint_region_scales=(3, 7, 13, 24, 38),
        sat0=0.55,
        sat1=0.94,
        v0=0.60,
        v1=0.92,
        spec_uf=180,
        spec_vf=176,
        spec_warp=0.030,
        spec_cycles_x=640,
        spec_cycles_y=616,
        spec_cycles_diag=552,
        tint=(0.88, 1.08, 1.02),
        m_hi=228,
        m_lo=42,
        r_hi=16,
        r_lo=96,
        cc_hi=22,
        cc_lo=58,
        desc="PRISM FORGE Bright Seafoam Bolt — seafoam/lime voltage on bright shell; undertone through micro hue.",
    ),
    _row(
        id="pf_bright_cerulean_pop",
        seed_off=9628,
        hue_c=0.58,
        hue_span=0.16,
        paint_hue_gain=0.09,
        paint_region_scales=(3, 6, 12, 21, 36),
        sat0=0.68,
        sat1=0.98,
        v0=0.62,
        v1=0.94,
        spec_uf=188,
        spec_vf=168,
        spec_warp=0.031,
        spec_cycles_x=676,
        spec_cycles_y=588,
        spec_cycles_diag=522,
        tint=(0.88, 0.96, 1.14),
        m_hi=242,
        m_lo=32,
        r_hi=15,
        r_lo=110,
        cc_hi=19,
        cc_lo=66,
        desc="PRISM FORGE Bright Cerulean Pop — saturated sky blue; sparkle via HF spec, not albedo bands.",
    ),
    _row(
        id="pf_bright_canary_glass",
        seed_off=9629,
        hue_c=0.16,
        hue_span=0.12,
        paint_hue_gain=0.088,
        paint_region_scales=(3, 5, 10, 18, 30),
        sat0=0.52,
        sat1=0.90,
        v0=0.72,
        v1=0.96,
        spec_uf=172,
        spec_vf=174,
        spec_warp=0.028,
        spec_cycles_x=624,
        spec_cycles_y=608,
        spec_cycles_diag=558,
        m_hi=220,
        m_lo=48,
        r_hi=17,
        r_lo=88,
        cc_hi=24,
        cc_lo=54,
        desc="PRISM FORGE Bright Canary Glass — lemon-lime glass bright plate; satin-glass spec envelope.",
    ),
    _row(
        id="pf_bright_magenta_arc",
        seed_off=9630,
        hue_c=0.88,
        hue_span=0.20,
        paint_hue_gain=0.10,
        paint_region_scales=(3, 6, 13, 23, 38),
        sat0=0.65,
        sat1=0.99,
        v0=0.55,
        v1=0.88,
        spec_uf=190,
        spec_vf=160,
        spec_warp=0.032,
        spec_cycles_x=690,
        spec_cycles_y=598,
        spec_cycles_diag=528,
        m_hi=238,
        m_lo=36,
        r_hi=15,
        r_lo=114,
        cc_hi=20,
        cc_lo=68,
        desc="PRISM FORGE Bright Magenta Arc — hot magenta/fuchsia with micro hue arc; no macro stripes.",
    ),
    _row(
        id="pf_bright_lime_voltage",
        seed_off=9631,
        hue_c=0.22,
        hue_span=0.16,
        paint_hue_gain=0.11,
        paint_region_scales=(3, 7, 14, 26, 40),
        sat0=0.58,
        sat1=0.98,
        v0=0.58,
        v1=0.90,
        spec_uf=186,
        spec_vf=172,
        spec_warp=0.033,
        spec_cycles_x=702,
        spec_cycles_y=582,
        spec_cycles_diag=518,
        tint=(0.92, 1.12, 0.88),
        m_hi=244,
        m_lo=30,
        r_hi=15,
        r_lo=106,
        cc_hi=18,
        cc_lo=62,
        desc="PRISM FORGE Bright Lime Voltage — acid lime on bright value; undertone via micro yellow-green walk.",
    ),
    _row(
        id="pf_bright_peach_fizz",
        seed_off=9632,
        hue_c=0.06,
        hue_span=0.14,
        paint_hue_gain=0.095,
        paint_region_scales=(3, 6, 12, 22, 36),
        sat0=0.50,
        sat1=0.88,
        v0=0.64,
        v1=0.92,
        spec_uf=178,
        spec_vf=166,
        spec_warp=0.030,
        spec_cycles_x=656,
        spec_cycles_y=606,
        spec_cycles_diag=542,
        tint=(1.10, 0.94, 0.90),
        m_hi=226,
        m_lo=44,
        r_hi=16,
        r_lo=94,
        cc_hi=22,
        cc_lo=56,
        desc="PRISM FORGE Bright Peach Fizz — warm peach/coral bright shell; fizz is spec HF, not peach stripes.",
    ),
    _row(
        id="pf_bright_neon_ice_stream",
        seed_off=9633,
        hue_c=0.52,
        hue_span=0.20,
        paint_hue_gain=0.10,
        paint_region_scales=(3, 6, 12, 22, 38),
        sat0=0.60,
        sat1=0.98,
        v0=0.62,
        v1=0.94,
        spec_uf=182,
        spec_vf=180,
        spec_warp=0.031,
        spec_cycles_x=664,
        spec_cycles_y=612,
        spec_cycles_diag=534,
        tint=(0.86, 0.98, 1.12),
        m_hi=234,
        m_lo=38,
        r_hi=16,
        r_lo=100,
        cc_hi=21,
        cc_lo=60,
        desc="PRISM FORGE Bright Neon Ice Stream — electric cyan/ice blue bright plate; arctic undertone.",
    ),
    _row(
        id="pf_bright_orchid_pulse",
        seed_off=9634,
        hue_c=0.82,
        hue_span=0.18,
        paint_hue_gain=0.10,
        paint_region_scales=(3, 7, 13, 24, 40),
        sat0=0.58,
        sat1=0.96,
        v0=0.56,
        v1=0.88,
        spec_uf=188,
        spec_vf=164,
        spec_warp=0.032,
        spec_cycles_x=682,
        spec_cycles_y=590,
        spec_cycles_diag=526,
        tint=(1.06, 0.90, 1.08),
        m_hi=236,
        m_lo=36,
        r_hi=15,
        r_lo=112,
        cc_hi=20,
        cc_lo=66,
        desc="PRISM FORGE Bright Orchid Pulse — vivid orchid/violet bright finish; pulse in spec, not candy bands.",
    ),
    _row(
        id="pf_blend_triad_mist",
        seed_off=9635,
        hue_c=0.55,
        hue_span=0.42,
        paint_hue_gain=0.088,
        paint_region_scales=(3, 6, 13, 24, 40),
        rgb_flake=((0.16, 0.50, 0.54), (0.40, 0.20, 0.56), (0.74, 0.58, 0.26), (0.52, 0.62, 0.70)),
        rgb_flake_sharp=11.0,
        rgb_flake_micro=0.05,
        rgb_flake_lum_pulse=0.10,
        sat0=0.32,
        sat1=0.78,
        v0=0.18,
        v1=0.52,
        spec_uf=184,
        spec_vf=168,
        spec_warp=0.034,
        spec_cycles_x=670,
        spec_cycles_y=600,
        spec_cycles_diag=530,
        m_hi=238,
        m_lo=32,
        r_hi=15,
        r_lo=116,
        cc_hi=19,
        cc_lo=70,
        desc="PRISM FORGE Blend Triad Mist — three-hue mist (teal/violet/gold) crushed to micro scales.",
    ),
    _row(
        id="pf_blend_quad_weave",
        seed_off=9636,
        hue_c=0.45,
        hue_span=0.48,
        paint_hue_gain=0.092,
        paint_region_scales=(3, 7, 14, 26, 42),
        rgb_flake=((0.10, 0.50, 0.38), (0.46, 0.18, 0.54), (0.80, 0.64, 0.24), (0.20, 0.24, 0.30)),
        rgb_flake_sharp=11.0,
        rgb_flake_micro=0.05,
        rgb_flake_lum_pulse=0.10,
        sat0=0.36,
        sat1=0.82,
        v0=0.14,
        v1=0.48,
        spec_uf=192,
        spec_vf=170,
        spec_warp=0.035,
        spec_cycles_x=696,
        spec_cycles_y=586,
        spec_cycles_diag=512,
        m_hi=242,
        m_lo=28,
        r_hi=15,
        r_lo=120,
        cc_hi=18,
        cc_lo=72,
        desc="PRISM FORGE Blend Quad Weave — four-hue weave in micro field; spec carries extra separation.",
    ),
    _row(
        id="pf_spectrum_chaos_crown",
        seed_off=9637,
        hue_c=0.08,
        hue_span=0.92,
        paint_hue_gain=0.11,
        paint_region_scales=(2, 4, 8, 14, 24),
        hue_palette=(0.0, 0.11, 0.24, 0.38, 0.52, 0.66, 0.80, 0.93),
        hue_palette_jitter=0.44,
        sat0=0.42,
        sat1=0.92,
        v0=0.10,
        v1=0.48,
        spec_uf=206,
        spec_vf=188,
        spec_warp=0.040,
        spec_cycles_x=748,
        spec_cycles_y=552,
        spec_cycles_diag=478,
        tri_power=0.34,
        spec_ultra_weight=0.56,
        m_hi=246,
        m_lo=22,
        r_hi=15,
        r_lo=128,
        cc_hi=18,
        cc_lo=78,
        desc="PRISM FORGE Spectrum Chaos Crown — full-spectrum madness #1: max hue span, still pixel-crushed on albedo.",
    ),
    _row(
        id="pf_prismatic_void_madness",
        seed_off=9638,
        hue_c=0.72,
        hue_span=0.88,
        paint_hue_gain=0.10,
        paint_region_scales=(2, 5, 9, 16, 28),
        hue_palette=(0.72, 0.84, 0.94, 0.06, 0.18, 0.32, 0.48, 0.62),
        hue_palette_jitter=0.42,
        sat0=0.38,
        sat1=0.90,
        v0=0.06,
        v1=0.42,
        spec_uf=202,
        spec_vf=194,
        spec_warp=0.042,
        spec_cycles_x=762,
        spec_cycles_y=548,
        spec_cycles_diag=468,
        tri_power=0.32,
        m_hi=248,
        m_lo=20,
        r_hi=15,
        r_lo=130,
        cc_hi=18,
        cc_lo=80,
        desc="PRISM FORGE Prismatic Void Madness — full-spectrum madness #2 on deep void; rainbow in spec + micro hue.",
    ),
    _row(
        id="pf_white_castle_of_fear",
        seed_off=9639,
        hue_c=0.54,
        hue_span=0.06,
        paint_hue_gain=0.055,
        paint_region_scales=(2, 4, 8, 14, 24),
        micro_hue_amp=0.012,
        sat0=0.04,
        sat1=0.22,
        v0=0.88,
        v1=0.99,
        spec_uf=168,
        spec_vf=182,
        spec_warp=0.026,
        spec_cycles_x=598,
        spec_cycles_y=622,
        spec_cycles_diag=572,
        ridge_gamma=1.55,
        tint=(0.96, 0.98, 1.08),
        m_hi=232,
        m_lo=52,
        r_hi=17,
        r_lo=84,
        cc_hi=26,
        cc_lo=50,
        desc="PRISM FORGE White Castle of Fear — glimmering white show plate; ice-blue undertone via tint + micro hue.",
    ),
    _row(
        id="pf_gradient_venetian_veil",
        seed_off=9640,
        hue_c=0.62,
        hue_span=0.28,
        paint_hue_gain=0.078,
        paint_region_scales=(4, 10, 24, 48, 80),
        paint_region_weights=(0.18, 0.22, 0.24, 0.20, 0.16),
        sat0=0.22,
        sat1=0.62,
        v0=0.20,
        v1=0.56,
        spec_uf=176,
        spec_vf=172,
        spec_warp=0.032,
        spec_cycles_x=638,
        spec_cycles_y=608,
        spec_cycles_diag=548,
        m_hi=222,
        m_lo=46,
        r_hi=16,
        r_lo=92,
        cc_hi=23,
        cc_lo=54,
        desc="PRISM FORGE Gradient Venetian Veil — soft multi-octave gradient bias in region scales + micro crush.",
    ),
    _row(
        id="pf_tri_crimson_cyan_mage",
        seed_off=9641,
        hue_c=0.02,
        hue_span=0.50,
        paint_hue_gain=0.09,
        paint_region_scales=(3, 7, 15, 28, 46),
        rgb_flake=((0.78, 0.08, 0.14), (0.04, 0.74, 0.86), (0.62, 0.10, 0.56), (0.16, 0.04, 0.22)),
        rgb_flake_sharp=12.0,
        rgb_flake_micro=0.052,
        rgb_flake_lum_pulse=0.10,
        sat0=0.48,
        sat1=0.92,
        v0=0.10,
        v1=0.50,
        spec_uf=188,
        spec_vf=166,
        spec_warp=0.035,
        spec_cycles_x=686,
        spec_cycles_y=594,
        spec_cycles_diag=520,
        tint=(1.04, 0.96, 0.98),
        m_hi=240,
        m_lo=30,
        r_hi=15,
        r_lo=118,
        cc_hi=18,
        cc_lo=70,
        desc="PRISM FORGE Tri Crimson Cyan Mage — crimson/cyan/magenta triad on micro islands; mage undertone in spec.",
    ),
    _row(
        id="pf_quad_jade_violet_gold_slate",
        seed_off=9642,
        hue_c=0.42,
        hue_span=0.38,
        paint_hue_gain=0.086,
        paint_region_scales=(3, 6, 14, 26, 44),
        rgb_flake=((0.08, 0.50, 0.38), (0.40, 0.16, 0.52), (0.82, 0.66, 0.22), (0.18, 0.22, 0.28)),
        rgb_flake_sharp=11.0,
        rgb_flake_micro=0.05,
        rgb_flake_lum_pulse=0.10,
        sat0=0.34,
        sat1=0.78,
        v0=0.12,
        v1=0.48,
        spec_uf=184,
        spec_vf=170,
        spec_warp=0.034,
        spec_cycles_x=672,
        spec_cycles_y=602,
        spec_cycles_diag=528,
        m_hi=236,
        m_lo=34,
        r_hi=15,
        r_lo=114,
        cc_hi=19,
        cc_lo=68,
        desc="PRISM FORGE Quad Jade Violet Gold Slate — four-tone luxury blend; all crushed to fine texture.",
    ),
    _row(
        id="pf_fade_copper_teal_sunset",
        seed_off=9643,
        hue_c=0.08,
        hue_span=0.36,
        paint_hue_gain=0.082,
        paint_region_scales=(5, 12, 28, 56, 96),
        paint_region_weights=(0.16, 0.20, 0.24, 0.22, 0.18),
        rgb_flake=((0.62, 0.30, 0.16), (0.82, 0.46, 0.20), (0.10, 0.52, 0.56), (0.92, 0.60, 0.26), (0.06, 0.20, 0.36)),
        rgb_flake_sharp=10.5,
        rgb_flake_micro=0.05,
        rgb_flake_lum_pulse=0.11,
        sat0=0.36,
        sat1=0.82,
        v0=0.18,
        v1=0.54,
        spec_uf=180,
        spec_vf=164,
        spec_warp=0.033,
        spec_cycles_x=658,
        spec_cycles_y=610,
        spec_cycles_diag=538,
        tint=(1.04, 0.97, 0.92),
        m_hi=230,
        m_lo=38,
        r_hi=16,
        r_lo=104,
        cc_hi=21,
        cc_lo=60,
        desc="PRISM FORGE Fade Copper Teal Sunset — copper→teal sunset gradient character via **region octaves** + micro.",
    ),
    _row(
        id="pf_blend_ocean_peach_ivory",
        seed_off=9644,
        hue_c=0.52,
        hue_span=0.22,
        paint_hue_gain=0.075,
        paint_region_scales=(3, 8, 18, 36, 64),
        paint_region_weights=(0.18, 0.20, 0.22, 0.22, 0.18),
        rgb_flake=((0.16, 0.48, 0.62), (0.10, 0.38, 0.50), (0.98, 0.48, 0.40), (0.98, 0.95, 0.88), (0.92, 0.66, 0.52)),
        rgb_flake_scale_sets=((1, 2, 3), (1, 2, 3), (1, 2, 4), (1, 2, 3), (1, 2, 4)),
        rgb_flake_sharp=9.5,
        rgb_flake_logit_hf=0.085,
        rgb_flake_region_amp=0.02,
        rgb_flake_micro=0.038,
        rgb_flake_lum_pulse=0.055,
        sat0=0.18,
        sat1=0.58,
        v0=0.42,
        v1=0.82,
        spec_uf=172,
        spec_vf=176,
        spec_warp=0.029,
        spec_cycles_x=628,
        spec_cycles_y=614,
        spec_cycles_diag=556,
        tint=(1.02, 0.99, 0.97),
        m_hi=214,
        m_lo=54,
        r_hi=18,
        r_lo=78,
        cc_hi=25,
        cc_lo=50,
        desc="PRISM FORGE Blend Ocean Peach Ivory — pastel tri-hue on ivory value; beach luxury micro spec.",
    ),
    _row(
        id="pf_iris_velvet_crossfade",
        seed_off=9645,
        hue_c=0.76,
        hue_span=0.30,
        paint_hue_gain=0.080,
        paint_region_scales=(3, 7, 16, 32, 56),
        hue_palette=(0.70, 0.76, 0.82, 0.88, 0.94, 0.08),
        hue_palette_jitter=0.30,
        sat0=0.30,
        sat1=0.72,
        v0=0.14,
        v1=0.48,
        spec_uf=186,
        spec_vf=168,
        spec_warp=0.033,
        spec_cycles_x=668,
        spec_cycles_y=598,
        spec_cycles_diag=526,
        m_hi=234,
        m_lo=34,
        r_hi=15,
        r_lo=112,
        cc_hi=20,
        cc_lo=66,
        desc="PRISM FORGE Iris Velvet Crossfade — iris/violet velvet crossfade; micro cross hue, no macro bands.",
    ),
    _row(
        id="pf_spectral_tidepool_wash",
        seed_off=9646,
        hue_c=0.50,
        hue_span=0.44,
        paint_hue_gain=0.088,
        paint_region_scales=(3, 6, 13, 26, 44),
        rgb_flake=((0.08, 0.48, 0.52), (0.20, 0.62, 0.46), (0.36, 0.18, 0.56), (0.52, 0.74, 0.78)),
        rgb_flake_sharp=11.0,
        rgb_flake_micro=0.05,
        rgb_flake_lum_pulse=0.10,
        sat0=0.36,
        sat1=0.84,
        v0=0.16,
        v1=0.52,
        spec_uf=190,
        spec_vf=172,
        spec_warp=0.035,
        spec_cycles_x=678,
        spec_cycles_y=592,
        spec_cycles_diag=518,
        tint=(0.96, 1.02, 1.02),
        m_hi=238,
        m_lo=32,
        r_hi=15,
        r_lo=116,
        cc_hi=19,
        cc_lo=68,
        desc="PRISM FORGE Spectral Tidepool Wash — teal/green/violet wash; tidepool spectral in HF spec.",
    ),
    _row(
        id="pf_midnight_coral_ember",
        seed_off=9647,
        hue_c=0.02,
        hue_span=0.28,
        paint_hue_gain=0.074,
        paint_region_scales=(3, 6, 12, 22, 40),
        rgb_flake=((0.03, 0.05, 0.12), (0.40, 0.06, 0.12), (0.90, 0.36, 0.26), (0.52, 0.10, 0.08)),
        rgb_flake_sharp=11.5,
        rgb_flake_micro=0.048,
        rgb_flake_lum_pulse=0.10,
        sat0=0.40,
        sat1=0.86,
        v0=0.06,
        v1=0.40,
        spec_uf=182,
        spec_vf=160,
        spec_warp=0.034,
        spec_cycles_x=662,
        spec_cycles_y=604,
        spec_cycles_diag=536,
        tint=(1.04, 0.94, 0.92),
        m_hi=236,
        m_lo=30,
        r_hi=15,
        r_lo=118,
        cc_hi=19,
        cc_lo=70,
        desc="PRISM FORGE Midnight Coral Ember — deep midnight with coral ember micro pockets + warm spec.",
    ),
    _row(
        id="pf_emerald_orchid_storm",
        seed_off=9648,
        hue_c=0.38,
        hue_span=0.46,
        paint_hue_gain=0.09,
        paint_region_scales=(3, 7, 15, 28, 46),
        rgb_flake=((0.06, 0.44, 0.32), (0.10, 0.58, 0.38), (0.50, 0.16, 0.46), (0.04, 0.20, 0.14)),
        rgb_flake_sharp=11.5,
        rgb_flake_micro=0.052,
        rgb_flake_lum_pulse=0.10,
        sat0=0.42,
        sat1=0.90,
        v0=0.10,
        v1=0.50,
        spec_uf=188,
        spec_vf=174,
        spec_warp=0.036,
        spec_cycles_x=690,
        spec_cycles_y=588,
        spec_cycles_diag=522,
        tint=(0.96, 1.02, 0.98),
        m_hi=242,
        m_lo=28,
        r_hi=15,
        r_lo=120,
        cc_hi=18,
        cc_lo=72,
        desc="PRISM FORGE Emerald Orchid Storm — emerald/jade/orchid tri-storm; crushed hue complexity.",
    ),
    _row(
        id="pf_golden_ultraviolet_fog",
        seed_off=9649,
        hue_c=0.12,
        hue_span=0.72,
        paint_hue_gain=0.095,
        paint_region_scales=(2, 5, 10, 18, 32),
        hue_palette=(0.12, 0.08, 0.82, 0.70, 0.16, 0.52, 0.78, 0.92),
        hue_palette_jitter=0.40,
        sat0=0.34,
        sat1=0.82,
        v0=0.12,
        v1=0.48,
        spec_uf=198,
        spec_vf=186,
        spec_warp=0.039,
        spec_cycles_x=722,
        spec_cycles_y=570,
        spec_cycles_diag=492,
        tri_power=0.36,
        spec_ultra_weight=0.54,
        tint=(1.08, 1.02, 0.92),
        m_hi=244,
        m_lo=24,
        r_hi=15,
        r_lo=124,
        cc_hi=18,
        cc_lo=76,
        desc="PRISM FORGE Golden Ultraviolet Fog — full-spectrum madness #3 (warmer): gold fog into UV violet micro travel.",
    ),
)


def _bind(cfg: dict):
    _c = dict(cfg)
    del _c["id"]
    del _c["desc"]

    def paint_fn(paint, shape, mask, seed, pm, bb):
        return _pf_paint(paint, shape, mask, seed, pm, bb, _c)

    def spec_fn(shape, seed, sm, base_m, base_r):
        return _pf_spec(shape, seed, sm, base_m, base_r, _c)

    fid = cfg["id"]
    paint_fn.__name__ = f"paint_{fid}"
    paint_fn.__doc__ = cfg["desc"]
    spec_fn.__name__ = f"spec_{fid}"
    spec_fn.__doc__ = cfg["desc"]
    return paint_fn, spec_fn


PRISM_FORGE_BASE_REGISTRY = {}
for _cfg in _PF_ROWS:
    _pid = _cfg["id"]
    _p, _s = _bind(_cfg)
    PRISM_FORGE_BASE_REGISTRY[_pid] = {
        "base_spec_fn": _s,
        "M": int((_cfg["m_hi"] + _cfg["m_lo"]) // 2),
        "R": int((_cfg["r_hi"] + _cfg["r_lo"]) // 2),
        "paint_fn": _p,
        "desc": _cfg["desc"],
    }

assert len(_PF_ROWS) == 50
assert len({r["seed_off"] for r in _PF_ROWS}) == 50
assert len({r["id"] for r in _PF_ROWS}) == 50
