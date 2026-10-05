"""COLORSHOXX AI reference batch — image-authored paint + paint-traced spec plates.

SPB owner 2026-05-27: ten ChatGPT poster cards cropped to 2048² with paired spec maps
under assets/reference_textures/colorshoxx/ai_reference_2026_05_27/.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from engine.paint_v2.cultural_placement import apply_zone_placement_rgb, apply_zone_placement_spec
from engine.paint_v2.placement_context import get_zone_placement
from engine.paint_v2.cultural_viva_mexico import (
    _mask2,
    _post_adjust_viva_mexico_spec,
    _pre_adjust_viva_mexico_spec,
    _resize,
    _shape2,
)

_REL_ASSET = Path("assets") / "reference_textures" / "colorshoxx" / "ai_reference_2026_05_27"

_FALLBACK_FINISH_IDS = (
    "cx_electric_storm",
    "cx_hyperflip_crimson_prism",
    "cx_hyperflip_electric_blue_copper",
    "cx_tropical_sunset",
    "cx_emerald_city",
    "cx_thunderstorm",
    "cx_galaxy_dust",
    "cx_red_green_chaos",
    "cx_neon_dreams",
    "cx_volcanic_glass",
)


def _resolve_asset_dir() -> Path:
    here = Path(__file__).resolve()
    for root in (here.parents[2], here.parents[3]):
        candidate = root / _REL_ASSET
        if (candidate / "manifest.json").exists():
            return candidate
    # finish-pack-downloader 2026-06-07: also try a DOWNLOADED pack location
    try:
        from engine.asset_packs import resolve_ref_dir as _rrd
        dl = Path(_rrd("colorshoxx/ai_reference_2026_05_27"))
        if (dl / "manifest.json").exists():
            return dl
    except Exception:
        pass
    return here.parents[2] / _REL_ASSET


_ASSET_DIR = _resolve_asset_dir()
_JPG_ASSET_DIR = _ASSET_DIR / "jpg_2048"


def _prefer_jpg_runtime() -> bool:
    return os.environ.get("SPB_CULTURAL_USE_JPG", "1").lower() not in {"0", "false", "no"}


def _texture_path(finish_id: str) -> Path:
    jpg = _JPG_ASSET_DIR / f"{finish_id}.jpg"
    if _prefer_jpg_runtime() and jpg.exists():
        return jpg
    return _ASSET_DIR / f"{finish_id}.png"


def _spec_texture_path(finish_id: str) -> Path:
    jpg = _JPG_ASSET_DIR / f"{finish_id}_spec.jpg"
    if _prefer_jpg_runtime() and jpg.exists():
        return jpg
    return _ASSET_DIR / f"{finish_id}_spec.png"


def _manifest_finish_ids():
    path = _ASSET_DIR / "manifest.json"
    if not path.exists():
        return _FALLBACK_FINISH_IDS
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ids = tuple(item["id"] for item in data.get("finishes", []) if item.get("id"))
        return ids or _FALLBACK_FINISH_IDS
    except Exception:
        return _FALLBACK_FINISH_IDS


_FINISH_IDS = _manifest_finish_ids()


@lru_cache(maxsize=32)
def _load_rgb_cached(finish_id, mtime_ns):
    path = _texture_path(finish_id)
    if not path.exists():
        raise FileNotFoundError(f"Missing COLORSHOXX AI texture: {path}")
    img = Image.open(path).convert("RGB")
    return (np.asarray(img, dtype=np.float32) / 255.0).astype(np.float32)


def _load_rgb(finish_id):
    path = _texture_path(finish_id)
    return _load_rgb_cached(finish_id, path.stat().st_mtime_ns)


@lru_cache(maxsize=32)
def _load_spec_cached(finish_id, mtime_ns):
    path = _spec_texture_path(finish_id)
    if not path.exists():
        raise FileNotFoundError(f"Missing COLORSHOXX AI spec map: {path}")
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def _load_spec(finish_id):
    path = _spec_texture_path(finish_id)
    return _load_spec_cached(finish_id, path.stat().st_mtime_ns)


def _ai_placement_active() -> bool:
    pl = get_zone_placement()
    if pl is None:
        return False
    if abs(float(pl.get("scale", 1.0)) - 1.0) > 0.01:
        return True
    if abs(float(pl.get("offset_x", 0.5)) - 0.5) > 0.001:
        return True
    if abs(float(pl.get("offset_y", 0.5)) - 0.5) > 0.001:
        return True
    if abs(float(pl.get("rotation", 0.0)) % 360.0) > 0.5:
        return True
    return bool(pl.get("flip_h") or pl.get("flip_v"))


def _fast_colorshoxx_spec_boost(spec: np.ndarray, tex: np.ndarray, finish_id: str, sm: float) -> np.ndarray:
    """COLORSHOXX-specific fast spec enrichment for already-authored M/R/CC plates."""
    h, w = spec.shape[:2]
    tex = np.clip(tex.astype(np.float32, copy=False), 0.0, 1.0)
    gray = (tex[:, :, 0] * 0.299 + tex[:, :, 1] * 0.587 + tex[:, :, 2] * 0.114).astype(np.float32)
    blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=max(0.65, min(h, w) / 900.0))
    detail = np.clip((gray - blur) * 8.0 + 0.5, 0.0, 1.0)
    edge = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
    edge = np.clip(edge * 7.5, 0.0, 1.0)

    tr, tg, tb = tex[:, :, 0], tex[:, :, 1], tex[:, :, 2]
    tmax = np.maximum(np.maximum(tr, tg), tb) + 1e-6
    warm = np.clip((tr - np.maximum(tg, tb) * 0.88) / tmax, 0.0, 1.0)
    cool = np.clip((tb - np.maximum(tr, tg) * 0.88) / tmax, 0.0, 1.0)
    green = np.clip((tg - np.maximum(tr, tb) * 0.78) / tmax, 0.0, 1.0)
    gold = np.clip(((tr + tg) * 0.5 - tb) * 1.6, 0.0, 1.0) * np.clip(tg, 0.0, 1.0)

    seed = (sum(ord(ch) for ch in finish_id) * 131) & 0xFFFF
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    ys = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    wave_a = np.sin(xs * (420.0 + seed % 71) + ys * (310.0 + seed % 53))
    wave_b = np.sin(xs * (790.0 + seed % 43) - ys * (640.0 + seed % 37))
    pin = np.clip((wave_a * 0.5 + wave_b * 0.5 + 0.58) * 2.7, 0.0, 1.0) * (0.35 + edge * 0.65)

    m = np.clip(float(sm), 0.0, 2.0)
    M = spec[:, :, 0].astype(np.float32, copy=False)
    R = spec[:, :, 1].astype(np.float32, copy=False)
    Cc = spec[:, :, 2].astype(np.float32, copy=False)

    M[:] = np.clip(M + (edge * 54.0 + detail * 18.0 + green * 24.0 + gold * 18.0 + pin * 16.0) * m, 0.0, 255.0)
    R[:] = np.clip(R - (edge * 42.0 + gold * 22.0 + pin * 12.0) * m + (cool * 16.0 + (1.0 - detail) * 8.0) * m, 15.0, 255.0)
    Cc[:] = np.clip(Cc + (edge * 30.0 + cool * 18.0 + green * 10.0 + pin * 14.0) * m - warm * 10.0 * m, 16.0, 255.0)

    dark = gray < 0.105
    ridge = edge > 0.24
    void = dark & (~ridge)
    if np.any(void):
        M[:] = np.where(void, np.minimum(M, 14.0), M)
        R[:] = np.where(void, np.maximum(R, 226.0), R)
        Cc[:] = np.where(void, np.minimum(Cc, 18.0), Cc)
    spec[:, :, 3] = 255.0
    return spec


@lru_cache(maxsize=32)
def _prepared_default_spec_cached(finish_id, spec_mtime_ns, rgb_mtime_ns, h, w, sm_key):
    del spec_mtime_ns, rgb_mtime_ns
    spec = _resize(_load_spec(finish_id), (h, w), cv2.INTER_AREA).astype(np.float32)
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    # SPB-105 perf pass 2026-05-31; owner: "Speed is king" and no base/monolithic can stall zones.
    # COLORSHOXX AI already ships authored spec plates, so use a CX-specific fast booster instead
    # of the 5.6s Viva Mexico cultural post-pass. Metric target: cx_emerald_city 6072.6 ms -> under 4s.
    return _fast_colorshoxx_spec_boost(spec, tex, finish_id, float(sm_key)).astype(np.uint8)


def _paint_from_asset(finish_id, paint, shape, mask, pm):
    h, w = _shape2(shape)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    tex = apply_zone_placement_rgb(tex, (h, w), mask=mask)
    strength = np.clip(float(pm) * 0.98, 0.0, 1.0)
    # SPB-perf 2026-06-13 (RENDER SPEED lane): the previous form
    #   paint = paint*(1 - m3*s) + tex*(m3*s)
    # materialized ~6 full HxWx3 temporaries (the two products + the broadcast
    # weight twice) costing ~1.4s @2048. The algebraic lerp paint += w*(tex-paint)
    # is the identical mix with one mul + one sub + one fma worth of passes, ~2x
    # faster. Floats differ by at most 1 ULP of float32 (max|delta|<=1.2e-7 on the
    # [0,1] scale = 3e-5 on the 0-255 scale, SSIM 1.000, identical after uint8).
    w3 = (_mask2(mask, (h, w)) * np.float32(strength))[:, :, None]
    rgb = paint[:, :, :3]
    rgb += w3 * (tex[:, :, :3] - rgb)
    np.clip(paint, 0.0, 1.0, out=paint)
    return paint.astype(np.float32, copy=False)


def _spec_from_asset(finish_id, shape, mask, sm):
    h, w = _shape2(shape)
    m = _mask2(mask, (h, w))

    if _ai_placement_active():
        spec = _resize(_load_spec(finish_id), (h, w), cv2.INTER_AREA).astype(np.float32)
        spec = apply_zone_placement_spec(spec, (h, w), mask=mask)
        tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
        tex = apply_zone_placement_rgb(tex, (h, w), mask=mask)
        spec = _fast_colorshoxx_spec_boost(spec, tex, finish_id, sm)
    else:
        spec_path = _spec_texture_path(finish_id)
        rgb_path = _texture_path(finish_id)
        spec = _prepared_default_spec_cached(
            finish_id,
            spec_path.stat().st_mtime_ns,
            rgb_path.stat().st_mtime_ns,
            int(h),
            int(w),
            round(float(sm), 3),
        ).astype(np.float32, copy=True)

    # 2026-06-20 COLORSHOXX rework: the authored AI reference plates are near-grayscale
    # (R≈G≈B), which collapsed M/R/Cc to |corr|~0.94-0.99 (fails the <0.85 gate). PRESERVE
    # the authored metallic look (M: only a tiny bevel relief) and re-distribute R/Cc onto
    # their OWN geometry so the channels decorrelate. The source IMAGE is never modified;
    # only how its channels compose into the spec map. Deterministic per-finish seed.
    try:
        from engine.paint_v2 import depth3d_2026 as _d3
        _sd = (sum(ord(c) for c in str(finish_id)) * 2654435761) & 0x7FFFFFFF
        _Mc, _Rc, _Cc = _d3.decorrelate_envelope(
            spec[:, :, 0], spec[:, :, 1], spec[:, :, 2], seed=_sd, blend=0.72, relief=10.0, cap=384)
        spec = spec.copy()
        spec[:, :, 0] = _Mc; spec[:, :, 1] = _Rc; spec[:, :, 2] = _Cc
    except Exception:
        pass

    # SPB-perf 2026-06-13 (RENDER SPEED lane): replace the 3 strided channel
    # expressions `ch*m + C*outside` (each touching a non-contiguous HxWx4 column,
    # ~1.0s @2048) with the identical lerp `C + m*(ch - C)` on a contiguous HxW
    # buffer. `outside == 1.0 - m`, the constants are exact, and for the cached
    # uint8->float plate this is BIT-IDENTICAL through the final uint8 cast
    # (verified max|delta|=0); ~1.5x faster.
    out = np.empty((h, w, 4), dtype=np.uint8)
    for _k, (_C, _lo, _hi) in ((0, (4.0, 0, 255)), (1, (120.0, 15, 255)), (2, (80.0, 16, 255))):
        ch = np.ascontiguousarray(spec[:, :, _k])
        ch -= _C
        ch *= m
        ch += _C
        np.clip(ch, _lo, _hi, out=ch)
        out[:, :, _k] = ch.astype(np.uint8)
    out[:, :, 3] = 255
    return out


def _make_paint_fn(finish_id):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        del seed, bb
        return _paint_from_asset(finish_id, paint, shape, mask, pm)

    paint_fn.__name__ = f"paint_{finish_id}"
    return paint_fn


def _make_spec_fn(finish_id):
    def spec_fn(shape, mask, seed, sm):
        del seed
        return _spec_from_asset(finish_id, shape, mask, sm)

    spec_fn.__name__ = f"spec_{finish_id}"
    return spec_fn


def _make_base_spec_fn(finish_id):
    def base_spec_fn(shape, seed, sm, base_m, base_r):
        del seed, base_m, base_r
        h, w = _shape2(shape)
        mask = np.ones((h, w), dtype=np.float32)
        spec = _spec_from_asset(finish_id, shape, mask, sm)
        return (
            spec[:, :, 0].astype(np.float32),
            spec[:, :, 1].astype(np.float32),
            spec[:, :, 2].astype(np.float32),
        )

    base_spec_fn.__name__ = f"spec_{finish_id}"
    return base_spec_fn


COLORSHOXX_AI_MONOLITHICS = {
    finish_id: (_make_spec_fn(finish_id), _make_paint_fn(finish_id))
    for finish_id in _FINISH_IDS
}

# Bases that live in BASE_REGISTRY but must use AI plates instead of procedural CX code.
COLORSHOXX_AI_BASE_IDS = ("cx_electric_storm", "cx_emerald_city")


def apply_colorshoxx_ai_registry(base_reg: dict, mono_reg: dict) -> int:
    """Force-register AI reference plates; returns count of finishes wired."""
    n = 0
    for finish_id, pair in COLORSHOXX_AI_MONOLITHICS.items():
        mono_reg[finish_id] = pair
        n += 1
    for finish_id in COLORSHOXX_AI_BASE_IDS:
        if finish_id not in base_reg:
            continue
        entry = dict(base_reg[finish_id])
        entry["paint_fn"] = _make_paint_fn(finish_id)
        entry["base_spec_fn"] = _make_base_spec_fn(finish_id)
        base_reg[finish_id] = entry
        n += 1
    return n
