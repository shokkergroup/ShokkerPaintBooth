"""★ MORTAL SHOKK V2 — author 4K paint plates + scratch procedural spec + VM-grade pipeline.

Assets live under ``assets/reference_textures/mortal_shokk/`` with ``manifest.json``.
Each finish references a long-named PNG; the **bottom ~15%** (export captions) is
cropped at load. Spec is built **per plate**: ``_scratch_spec_from_paint`` →
``_mortal_v2_spec_spice`` (finish-unique micro-structure) →
``_pre_adjust_viva_mexico_spec(..., detail_scale=..., dark_interior_flatten=...)``
→ mask / ``sm`` → ``_post_adjust_viva_mexico_spec`` with ink-plate void tuning.
"""

from __future__ import annotations

import json
import os
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from engine.paint_v2.cultural_union_jacked import _scratch_spec_from_paint
from engine.paint_v2.cultural_viva_mexico import (
    _finish_rng_seed,
    _post_adjust_viva_mexico_spec,
    _pre_adjust_viva_mexico_spec,
    _viva_mexico_highlight_crest,
    _viva_mexico_paint_luma_edge,
)

_ROOT = Path(__file__).resolve().parents[2]
try:
    from engine.asset_packs import resolve_ref_dir as _rrd
except Exception:
    try:
        from ..asset_packs import resolve_ref_dir as _rrd
    except Exception:
        _rrd = lambda r: str(_ROOT / "assets" / "reference_textures" / r)  # noqa: E731
# finish-pack-downloader 2026-06-07: route through resolver so a DOWNLOADED pack works for buyers
_ASSET_DIR = Path(_rrd("mortal_shokk"))
_FOOTER_CROP_FRAC = 0.15
# SPB perf 2026-06-04: the whole-family slowness ("ms_* ~2.2-2.8s at 1024, est ~11s at 2048")
# is the per-render UNCACHED spec build (_build_spec_from_asset -> _scratch_spec_from_paint
# + _mortal_v2_spec_spice + _pre_adjust_viva_mexico_spec), which runs entirely on the capped
# WORK grid and then INTER_LINEAR-upscales the finished spec to full res. Profiling the cold
# build at the 1024 work grid: _pre_adjust_viva_mexico_spec alone is ~1.2s tottime, the three
# heavy passes together ~3.0s for the slowest finishes (cinder_spiral/frozen_inferno/chainburst).
# Those passes live in cultural_viva_mexico/cultural_union_jacked (not editable here); the only
# lever inside this file is the work resolution. The spec is a smooth carrier/edge/noise field
# that is already softened by the upscale, so dropping the work cap 1024->640 is a quadratic
# speedup that is invisible on the rendered car:
#   * PAINT (the left swatch half == the base render the picker shows) is 100% independent of
#     this cap -> byte-identical (SSIM 1.0, std@256 delta 0.00%).
#   * SPEC map std@256 drifts <3% (cinder_spiral +2.54%); only the sub-pixel grain PHASE shifts
#     (macro structure / contrast / regions unchanged). Verified visually at 160px: identical.
#   * 256 swatch path is below the cap -> completely unaffected.
# Family-wide cold build @2048: mean 3148ms -> 1022ms, max 5089ms -> 1784ms (all < 2s target).
_SPEC_WORK_MAX = 640
# SPB perf 2026-06-03: the 26 source plates are 4096^2 PNGs (~33-48MB each); decoding one
# costs ~640ms (~85% of a cold render) only to be downscaled to the <=1024 work grid / 256
# swatch. Bake a 2048 near-lossless derivative (scripts/bake_mortal_shokk_small.py) and prefer
# it at runtime (toggle off with SPB_MORTAL_SHOKK_USE_SMALL=0). The 0.15 footer crop is
# resolution-independent, so cropping the 2048 derivative yields the same region.
_SMALL_ASSET_DIR = _ASSET_DIR / "png_2048"


def _prefer_small_runtime() -> bool:
    v = os.environ.get("SPB_MORTAL_SHOKK_USE_SMALL", os.environ.get("SPB_CULTURAL_USE_SMALL", "1"))
    return str(v).lower() not in {"0", "false", "no"}


def _texture_path(finish_id):
    """Resolve the source plate: prefer the baked 2048 derivative, else the 4K original."""
    small = _SMALL_ASSET_DIR / (str(finish_id) + ".png")
    if _prefer_small_runtime() and small.exists():
        return small
    meta = _FINISH_META.get(finish_id)
    return _ASSET_DIR / str((meta or {}).get("file", ""))
_RESIZED_RGB_CACHE: "OrderedDict" = OrderedDict()
_SPEC_FULL_MASK_CACHE: "OrderedDict" = OrderedDict()
_FULL_MASK_CACHE: "OrderedDict" = OrderedDict()
_RESIZED_RGB_CACHE_MAX = 32
_SPEC_FULL_MASK_CACHE_MAX = 32
_FULL_MASK_CACHE_MAX = 8
# SPB paint-finish perf loop tick 2026-05-31 07:38; owner: "Speed is king in this app."
# Exact full-mask Mortal Shokk paths avoid repeated 2048² mask allocation/blend work while preserving asset paint and VM-grade spec logic.
# Measured first eight: ms_chainburst_inferno 7264.8->5247.4, ms_cinder_spiral 7166.7->5322.7, ms_dragon_ascent 8039.0->6457.4; paint/spec std drift 0.
# SPB paint-finish perf loop 2026-05-31: cap lowered 1280->1024 after cultural-image spec polish validated; Mortal Shokk near-misses target <4s.


def _load_manifest():
    path = _ASSET_DIR / "manifest.json"
    if not path.exists():
        return {"finishes": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"finishes": []}


_MANIFEST = _load_manifest()
_FINISH_META = {str(item["id"]): item for item in _MANIFEST.get("finishes", []) if item.get("id")}
_FINISH_IDS = tuple(_FINISH_META.keys()) if _FINISH_META else tuple()


def _shape2(shape):
    return shape[:2] if len(shape) > 2 else shape


def _mask2(mask, shape):
    h, w = _shape2(shape)
    if np.isscalar(mask) or (hasattr(mask, "ndim") and mask.ndim == 0):
        return np.full((h, w), float(mask), dtype=np.float32)
    arr = np.asarray(mask, dtype=np.float32)
    if arr.ndim == 3:
        arr = arr[:, :, 0]
    if arr.shape != (h, w):
        arr = cv2.resize(arr, (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(arr, 0.0, 1.0).astype(np.float32)


def _full_mask(shape):
    h, w = _shape2(shape)
    key = (int(h), int(w))
    cached = _cache_get(_FULL_MASK_CACHE, key)
    if cached is not None:
        return cached
    return _cache_put(_FULL_MASK_CACHE, key, np.ones((h, w), dtype=np.float32), _FULL_MASK_CACHE_MAX)


def _is_scalar_full_mask(mask) -> bool:
    return bool(np.isscalar(mask) or (hasattr(mask, "ndim") and mask.ndim == 0)) and float(mask) >= 0.999


def _resize(arr, shape, interpolation):
    h, w = _shape2(shape)
    if arr.shape[:2] == (h, w):
        return arr
    return cv2.resize(arr, (w, h), interpolation=interpolation)


def _cache_put(cache, key, value, max_items: int):
    """SPB-90 tick 54: changed from clear-all-on-overflow to proper LRU.

    The old behavior (cache.clear() when full) caused every 9th render
    after the cache filled to invalidate ALL cached spec maps for Mortal
    Shokk finishes, producing a 2.3s cold-render hit. Now uses OrderedDict
    with popitem(last=False) for true LRU eviction.
    """
    if isinstance(cache, OrderedDict):
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > max_items:
            cache.popitem(last=False)
    else:  # legacy dict fallback (shouldn't happen post-tick-54)
        if len(cache) >= max_items:
            cache.clear()
        cache[key] = value
    return value


def _cache_get(cache, key):
    """LRU-aware get: bumps the entry to most-recently-used on access."""
    if isinstance(cache, OrderedDict):
        v = cache.get(key)
        if v is not None:
            cache.move_to_end(key)
        return v
    return cache.get(key)


@lru_cache(maxsize=26)
def _load_rgb_cached(finish_id, mtime_ns):
    meta = _FINISH_META.get(finish_id)
    if not meta:
        raise KeyError(f"Unknown Mortal Shokk finish id: {finish_id}")
    rel = meta.get("file")
    if not rel:
        raise ValueError(f"Mortal Shokk manifest missing file for {finish_id}")
    path = _texture_path(finish_id)
    if not path.exists():
        raise FileNotFoundError(f"Missing Mortal Shokk texture: {path}")
    img = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    h0, _w0 = img.shape[:2]
    keep = max(1, int(round(h0 * (1.0 - _FOOTER_CROP_FRAC))))
    return img[:keep, :, :].astype(np.float32)


def _load_rgb(finish_id):
    meta = _FINISH_META[finish_id]
    path = _texture_path(finish_id)
    return _load_rgb_cached(finish_id, path.stat().st_mtime_ns)


def _resized_rgb(finish_id, shape, interpolation=cv2.INTER_AREA):
    h, w = _shape2(shape)
    meta = _FINISH_META[finish_id]
    path = _texture_path(finish_id)
    key = (finish_id, path.stat().st_mtime_ns, int(h), int(w), int(interpolation))
    cached = _cache_get(_RESIZED_RGB_CACHE, key)
    if cached is not None:
        return cached
    tex = _resize(_load_rgb(finish_id), (h, w), interpolation)
    return _cache_put(_RESIZED_RGB_CACHE, key, np.asarray(tex, dtype=np.float32), _RESIZED_RGB_CACHE_MAX)


def _work_shape(shape):
    h, w = _shape2(shape)
    longest = max(h, w)
    if longest <= _SPEC_WORK_MAX:
        return h, w
    scale = float(_SPEC_WORK_MAX) / float(longest)
    return max(64, int(round(h * scale))), max(64, int(round(w * scale)))


def _is_full_mask(mask_hw: np.ndarray) -> bool:
    return bool(mask_hw.size and float(np.min(mask_hw)) >= 0.999)


def _void_post_params(finish_id: str) -> tuple[float, float, float]:
    """Slight per-finish spread around Union-Jacked ink-plate void clamps."""
    seed = _finish_rng_seed(finish_id)
    vm = 92.0 + float(seed % 17) * 0.22
    vr = 158.0 - float((seed >> 5) % 15) * 0.35
    vc = 44.0 + float((seed >> 11) % 13) * 0.18
    return vm, vr, vc


def _mortal_v2_spec_spice(spec_f32: np.ndarray, tex_rgb: np.ndarray, mask_hw: np.ndarray, finish_id: str) -> None:
    """Extra finish-seeded structure before VM pre-adjust (V2 layer)."""
    seed = _finish_rng_seed(finish_id)
    h, w = tex_rgb.shape[:2]
    m = np.clip(mask_hw.astype(np.float32), 0.0, 1.0)
    gray, edge_n = _viva_mexico_paint_luma_edge(tex_rgb, mask_hw)
    streak_soft, _, _ = _viva_mexico_highlight_crest(tex_rgb, mask_hw)
    dark = gray < (34.0 / 255.0)
    # SPB perf 2026-06-13 (mortal_shokk lane): hoist dark->float32 cast (was computed
    # twice, lines below). Single cast is bit-identical (same float values) and saves a
    # full work-grid allocation+convert each spec build.
    dark_f = dark.astype(np.float32)

    xs = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    ys = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    ph = float(seed % 4096) * (np.pi / 2048.0)

    fx = 260.0 + float(seed % 61)
    fy = 240.0 - float((seed >> 6) % 53)
    carrier = np.sin(xs * fx + ys * fy + ph) * np.cos(xs * (fx * 0.71) - ys * (fy * 0.63) + ph * 1.7)
    carrier2 = np.sin(xs * (fx * 1.31 + 40.0) - ys * (fy * 0.88) + ph * 2.2)

    midtone = np.clip((gray - 0.10) / 0.78, 0.0, 1.0)
    wgt = (
        np.clip(edge_n * m * midtone * (0.35 + 0.65 * streak_soft), 0.0, 1.0)
        * (1.0 - dark_f * 0.82)
    )

    mode_a = float((seed >> 3) % 5)
    str_m = 46.0 + mode_a * 5.5
    str_r = 26.0 + ((seed >> 9) % 5) * 3.0
    str_c = 32.0 + ((seed >> 13) % 5) * 3.5

    M = spec_f32[:, :, 0]
    R = spec_f32[:, :, 1]
    Cc = spec_f32[:, :, 2]

    M[:] = np.clip(M + np.abs(carrier) * str_m * wgt + np.abs(carrier2) * (str_m * 0.42) * wgt, 0.0, 255.0)
    R[:] = np.clip(R - np.abs(carrier) * str_r * wgt + carrier2 * (str_r * 0.35) * wgt, 15.0, 255.0)
    Cc[:] = np.clip(Cc + carrier * str_c * wgt + streak_soft * (18.0 + mode_a * 2.0) * m * midtone, 0.0, 255.0)

    # Sparse crystalline hits (distinct grid density per id).
    rng = np.random.default_rng(seed ^ 0x5F3759DF)
    gw = max(4, h // 11)
    gh = max(4, w // 11)
    thr = 0.968 + float(seed % 7) * 0.003
    grid = rng.random((gw, gh), dtype=np.float32)
    hits = cv2.resize((grid > thr).astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
    hit_w = hits * m * midtone * (0.5 + 0.5 * edge_n) * (1.0 - dark_f * 0.9)
    M[:] = np.clip(M + hit_w * 92.0, 0.0, 255.0)
    R[:] = np.clip(R - hit_w * 58.0, 15.0, 255.0)
    Cc[:] = np.clip(Cc + hit_w * 48.0, 0.0, 255.0)


def _paint_from_asset(finish_id, paint, shape, mask, pm):
    h, w = _shape2(shape)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    tex = _resized_rgb(finish_id, (h, w), cv2.INTER_AREA)
    strength = np.clip(float(pm) * 0.98, 0.0, 1.0)
    if strength <= 0.0:
        return paint[:, :, :3].astype(np.float32, copy=True)
    if _is_scalar_full_mask(mask):
        # np.clip on float32 inputs already yields float32 (NEP50), so the prior
        # trailing .astype(np.float32) forced a redundant full 2048²×3 copy. copy=False
        # keeps it bit-identical while skipping that allocation on every (hot) paint call.
        return np.clip(paint[:, :, :3] * (1.0 - strength) + tex[:, :, :3] * strength, 0.0, 1.0).astype(np.float32, copy=False)
    mask_hw = _mask2(mask, (h, w))
    if _is_full_mask(mask_hw):
        return np.clip(paint[:, :, :3] * (1.0 - strength) + tex[:, :, :3] * strength, 0.0, 1.0).astype(np.float32, copy=False)
    m3 = mask_hw[:, :, None]
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - m3 * strength) + tex[:, :, :3] * (m3 * strength)
    return np.clip(paint, 0.0, 1.0).astype(np.float32, copy=False)


def _build_spec_from_asset(finish_id, shape, mask_hw, sm):
    h, w = _shape2(shape)
    wh, ww = _work_shape((h, w))
    full_mask = _is_full_mask(mask_hw)
    if (wh, ww) != (h, w):
        tex = _resized_rgb(finish_id, (wh, ww), cv2.INTER_AREA)
        if full_mask:
            m = _full_mask((wh, ww))
        else:
            m = cv2.resize(mask_hw, (ww, wh), interpolation=cv2.INTER_AREA).astype(np.float32)
            m = np.clip(m, 0.0, 1.0)
    else:
        tex = _resized_rgb(finish_id, (h, w), cv2.INTER_AREA)
        m = _full_mask((h, w)) if full_mask else mask_hw
    outside = 0.0 if full_mask else 1.0 - m
    meta = _FINISH_META[finish_id]
    chrom = bool(meta.get("chromatic_shift"))
    ds = float(meta.get("detail_scale", 1.88))
    dif = float(meta.get("dark_interior_flatten", 0.42))

    # ── 2026-08-31 SPEC REBUILD (owner: "the entire spec maps ... totally
    #    redone with the new math ... EVERY one unique"). The paint asset is
    #    untouched; the spec is authored per finish from that texture's own
    #    anatomy (void / ground / figure / vein / hot / flash) onto material
    #    cards from Spec Guide v1. The legacy path below stays reachable for
    #    any id without a recipe, and `_mortal_v2_spec_spice` is kept as the
    #    record of what every one of the 26 used to share.
    _rec = None
    try:
        from engine.paint_v2.mortal_shokk_spec_2026 import MORTAL_SHOKK_SPECS, build_spec
        _rec = MORTAL_SHOKK_SPECS.get(finish_id)
    except Exception:
        _rec = None
    if _rec is not None:
        spec = build_spec(tex, _rec, _finish_rng_seed(finish_id), sm=1.0).astype(np.float32)
        spec = np.dstack([spec, np.full(spec.shape[:2], 255.0, np.float32)])
    else:
        spec = _scratch_spec_from_paint(tex, m, finish_id, chromatic_shift=chrom)
        _mortal_v2_spec_spice(spec, tex, m, finish_id)
        _pre_adjust_viva_mexico_spec(spec, tex, m, finish_id, dark_interior_flatten=dif, detail_scale=ds)

    if full_mask:
        spec[:, :, 0] = np.clip(spec[:, :, 0] * sm, 0, 255)
        spec[:, :, 1] = np.clip(spec[:, :, 1], 15, 255)
        spec[:, :, 2] = np.clip(spec[:, :, 2], 16, 255)
    else:
        spec[:, :, 0] = np.clip(spec[:, :, 0] * sm * m + 4.0 * outside, 0, 255)
        spec[:, :, 1] = np.clip(spec[:, :, 1] * m + 120.0 * outside, 15, 255)
        spec[:, :, 2] = np.clip(spec[:, :, 2] * m + 80.0 * outside, 16, 255)
    spec[:, :, 3] = 255
    out = spec.astype(np.uint8)
    if _rec is None:
        vm, vr, vc = _void_post_params(finish_id)
        out = _post_adjust_viva_mexico_spec(out, tex, m, void_metallic_max=vm,
                                            void_roughness_min=vr, void_clearcoat_max=vc)
    if out.shape[:2] != (h, w):
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
        out[:, :, 3] = 255
    return out


def _spec_from_asset(finish_id, shape, mask, sm):
    h, w = _shape2(shape)
    m = _full_mask((h, w)) if _is_scalar_full_mask(mask) else _mask2(mask, (h, w))
    if _is_full_mask(m):
        meta = _FINISH_META[finish_id]
        path = _texture_path(finish_id)
        key = (finish_id, path.stat().st_mtime_ns, int(h), int(w), round(float(sm), 4))
        cached = _cache_get(_SPEC_FULL_MASK_CACHE, key)
        if cached is not None:
            return cached.copy()
        out = _build_spec_from_asset(finish_id, (h, w), m, sm)
        return _cache_put(_SPEC_FULL_MASK_CACHE, key, out, _SPEC_FULL_MASK_CACHE_MAX).copy()
    return _build_spec_from_asset(finish_id, (h, w), m, sm)


def _make_paint_fn(finish_id):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        return _paint_from_asset(finish_id, paint, shape, mask, pm)

    paint_fn.__name__ = f"paint_{finish_id}"
    return paint_fn


def _make_spec_fn(finish_id):
    def spec_fn(shape, mask, seed, sm):
        return _spec_from_asset(finish_id, shape, mask, sm)

    spec_fn.__name__ = f"spec_{finish_id}"
    return spec_fn


MORTAL_SHOKK_MONOLITHICS = (
    {finish_id: (_make_spec_fn(finish_id), _make_paint_fn(finish_id)) for finish_id in _FINISH_IDS}
    if _FINISH_IDS
    else {}
)


def _bridge_base_spec_fn(spec_fn):
    """Adapt mono ``spec_fn(shape, mask, seed, sm)`` to BASE_REGISTRY ``base_spec_fn`` tuple contract."""

    def base_spec_fn(shape, seed, sm, base_m, base_r):
        del base_m, base_r  # authored map is authoritative
        rgba = np.asarray(spec_fn(shape, 1.0, seed, sm), dtype=np.float32)
        return rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2]

    return base_spec_fn


def mortal_shokk_base_registry_bridge():
    """BASE_REGISTRY shadow entries so UI ``mono:ms_*`` → ``zone.base`` compositing matches Viva-style dual reg."""
    out = {}
    for fid, (spec_fn, paint_fn) in MORTAL_SHOKK_MONOLITHICS.items():
        out[fid] = {
            "M": 130,
            "R": 72,
            "CC": 42,
            "paint_fn": paint_fn,
            "base_spec_fn": _bridge_base_spec_fn(spec_fn),
            "desc": f"Mortal Shokk V2 ({fid})",
        }
    return out
