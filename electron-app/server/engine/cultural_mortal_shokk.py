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
_ASSET_DIR = _ROOT / "assets" / "reference_textures" / "mortal_shokk"
_FOOTER_CROP_FRAC = 0.15


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


def _resize(arr, shape, interpolation):
    h, w = _shape2(shape)
    if arr.shape[:2] == (h, w):
        return arr
    return cv2.resize(arr, (w, h), interpolation=interpolation)


@lru_cache(maxsize=64)
def _load_rgb_cached(finish_id, mtime_ns):
    meta = _FINISH_META.get(finish_id)
    if not meta:
        raise KeyError(f"Unknown Mortal Shokk finish id: {finish_id}")
    rel = meta.get("file")
    if not rel:
        raise ValueError(f"Mortal Shokk manifest missing file for {finish_id}")
    path = _ASSET_DIR / str(rel)
    if not path.exists():
        raise FileNotFoundError(f"Missing Mortal Shokk texture: {path}")
    img = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    h0, _w0 = img.shape[:2]
    keep = max(1, int(round(h0 * (1.0 - _FOOTER_CROP_FRAC))))
    return img[:keep, :, :].astype(np.float32)


def _load_rgb(finish_id):
    meta = _FINISH_META[finish_id]
    path = _ASSET_DIR / str(meta["file"])
    return _load_rgb_cached(finish_id, path.stat().st_mtime_ns)


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
        * (1.0 - dark.astype(np.float32) * 0.82)
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
    hit_w = hits * m * midtone * (0.5 + 0.5 * edge_n) * (1.0 - dark.astype(np.float32) * 0.9)
    M[:] = np.clip(M + hit_w * 92.0, 0.0, 255.0)
    R[:] = np.clip(R - hit_w * 58.0, 15.0, 255.0)
    Cc[:] = np.clip(Cc + hit_w * 48.0, 0.0, 255.0)


def _paint_from_asset(finish_id, paint, shape, mask, pm):
    h, w = _shape2(shape)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    m3 = _mask2(mask, (h, w))[:, :, None]
    strength = np.clip(float(pm) * 0.98, 0.0, 1.0)
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - m3 * strength) + tex[:, :, :3] * (m3 * strength)
    return np.clip(paint, 0.0, 1.0).astype(np.float32)


def _spec_from_asset(finish_id, shape, mask, sm):
    h, w = _shape2(shape)
    m = _mask2(mask, (h, w))
    outside = 1.0 - m
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    meta = _FINISH_META[finish_id]
    chrom = bool(meta.get("chromatic_shift"))
    ds = float(meta.get("detail_scale", 1.88))
    dif = float(meta.get("dark_interior_flatten", 0.42))

    spec = _scratch_spec_from_paint(tex, m, finish_id, chromatic_shift=chrom)
    _mortal_v2_spec_spice(spec, tex, m, finish_id)
    _pre_adjust_viva_mexico_spec(spec, tex, m, finish_id, dark_interior_flatten=dif, detail_scale=ds)

    spec[:, :, 0] = np.clip(spec[:, :, 0] * sm * m + 4.0 * outside, 0, 255)
    spec[:, :, 1] = np.clip(spec[:, :, 1] * m + 120.0 * outside, 15, 255)
    spec[:, :, 2] = np.clip(spec[:, :, 2] * m + 80.0 * outside, 16, 255)
    spec[:, :, 3] = 255
    vm, vr, vc = _void_post_params(finish_id)
    out = spec.astype(np.uint8)
    out = _post_adjust_viva_mexico_spec(out, tex, m, void_metallic_max=vm, void_roughness_min=vr, void_clearcoat_max=vc)
    return out


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
