"""Ricky reference-art spec overlays.

SPB-RATE10 2026-05-27 WWRD reference pass.
Owner verdict snippet: "MAKE THESE into 2048x2048 SPEC PATTERN OVERLAYS...
Like these exact one's here... apply the spec mapping logic for the 3 channels".
Metric movement is recorded after baking/rendering the ten reference-backed
overlays into RATE10 thumbnails.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from ..spec_patterns import _sm_scale, _validate_spec_output


_ROOT = Path(__file__).resolve().parents[2]
try:
    from engine.asset_packs import resolve_ref_dir as _rrd
except Exception:
    try:
        from ..asset_packs import resolve_ref_dir as _rrd
    except Exception:
        _rrd = lambda r: str(_ROOT / "assets" / "reference_textures" / r)  # noqa: E731
# finish-pack-downloader 2026-06-07: route through resolver so a DOWNLOADED pack works for buyers
_ASSET_DIR = Path(_rrd("spec_overlays/ricky_reference"))
_RESIZE_CACHE: "OrderedDict[tuple, np.ndarray]" = OrderedDict()
_CACHE_MAX = 32


def _load_manifest() -> dict:
    path = _ASSET_DIR / "manifest.json"
    if not path.exists():
        return {"finishes": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"finishes": []}


_MANIFEST = _load_manifest()
_META = {str(item["id"]): item for item in _MANIFEST.get("finishes", []) if item.get("id")}


def _shape2(shape) -> tuple[int, int]:
    return tuple(shape[:2]) if len(shape) > 2 else tuple(shape)


def _cache_put(key: tuple, value: np.ndarray) -> np.ndarray:
    _RESIZE_CACHE[key] = value
    _RESIZE_CACHE.move_to_end(key)
    while len(_RESIZE_CACHE) > _CACHE_MAX:
        _RESIZE_CACHE.popitem(last=False)
    return value


@lru_cache(maxsize=24)
def _load_spec_cached(finish_id: str, mtime_ns: int) -> np.ndarray:
    del mtime_ns
    meta = _META.get(finish_id)
    if not meta:
        raise KeyError(f"Unknown Ricky reference spec overlay: {finish_id}")
    path = _ASSET_DIR / str(meta["spec"])
    if not path.exists():
        raise FileNotFoundError(f"Missing Ricky reference spec: {path}")
    arr = np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32) / 255.0
    return arr[:, :, :3].astype(np.float32)


def _load_spec(finish_id: str) -> np.ndarray:
    meta = _META[finish_id]
    path = _ASSET_DIR / str(meta["spec"])
    return _load_spec_cached(finish_id, path.stat().st_mtime_ns)


def _reference_spec(finish_id: str, shape, seed, sm, **kwargs):
    del kwargs
    h, w = _shape2(shape)
    meta = _META.get(finish_id)
    if not meta:
        raise KeyError(f"Unknown Ricky reference spec overlay: {finish_id}")
    path = _ASSET_DIR / str(meta["spec"])
    key = (finish_id, path.stat().st_mtime_ns, int(h), int(w))
    cached = _RESIZE_CACHE.get(key)
    if cached is not None:
        _RESIZE_CACHE.move_to_end(key)
        # Perf 2026-06-13: `arr` is only READ below (never mutated in place),
        # so the defensive full-2048 copy of the cache entry was pure overhead
        # (~50ms/call). Read-only use keeps the cache uncorrupted.
        arr = cached
    else:
        src = _load_spec(finish_id)
        if src.shape[:2] == (h, w):
            arr = src.copy()
        else:
            arr = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)
        # _cache_put returns the stored object; reuse it directly (read-only).
        arr = _cache_put(key, arr)

    # Seed/sm modulation is deliberately subtle: the artwork is authoritative,
    # but these offsets make duplicate-zone uses feel alive under the lighting rig.
    phase = float((int(seed) + len(finish_id) * 97) % 4096) * (np.pi / 2048.0)
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    ys = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    shimmer = np.sin(xs * (73.0 + phase) + ys * (51.0 - phase * 0.37))
    micro = np.cos(xs * (211.0 - phase * 0.5) - ys * (179.0 + phase * 0.25))
    live = (shimmer * 0.012 + micro * 0.007).astype(np.float32)

    # Perf 2026-06-13: assemble channels straight into a preallocated (h,w,3)
    # buffer with `np.clip(..., out=...)`. This is bit-identical to the prior
    # `np.stack([M, R, CC]).astype(float32)` but skips stack's intermediate
    # plus the redundant astype copy (~190ms/call at 2048).
    out = np.empty((h, w, 3), dtype=np.float32)
    np.clip(arr[:, :, 0] + np.abs(live) * 0.045, 0.0, 1.0, out=out[:, :, 0])
    np.clip(arr[:, :, 1] + live * 0.035, 0.06, 0.98, out=out[:, :, 1])
    np.clip(arr[:, :, 2] - live * 0.030, 0.0, 1.0, out=out[:, :, 2])
    return _validate_spec_output(_sm_scale(out, sm), finish_id)


def ricky_viper_pit_hex(shape, seed, sm, **kwargs):
    return _reference_spec("viper_pit_hex", shape, seed, sm, **kwargs)


def ricky_wave_ripple(shape, seed, sm, **kwargs):
    return _reference_spec("wave_ripple", shape, seed, sm, **kwargs)


def ricky_samhain_ritual(shape, seed, sm, **kwargs):
    return _reference_spec("samhain_ritual", shape, seed, sm, **kwargs)


def ricky_ouija_mystic(shape, seed, sm, **kwargs):
    return _reference_spec("ouija_mystic", shape, seed, sm, **kwargs)


def ricky_stardust_fine(shape, seed, sm, **kwargs):
    return _reference_spec("stardust_fine", shape, seed, sm, **kwargs)


def ricky_spec_terrain_erosion(shape, seed, sm, **kwargs):
    return _reference_spec("spec_terrain_erosion", shape, seed, sm, **kwargs)


def ricky_spec_stress_fractures(shape, seed, sm, **kwargs):
    return _reference_spec("spec_stress_fractures", shape, seed, sm, **kwargs)


def ricky_spec_snake_scales(shape, seed, sm, **kwargs):
    return _reference_spec("spec_snake_scales", shape, seed, sm, **kwargs)


def ricky_spec_liquid_metal(shape, seed, sm, **kwargs):
    return _reference_spec("spec_liquid_metal", shape, seed, sm, **kwargs)


def ricky_spec_fresnel_gradient(shape, seed, sm, **kwargs):
    return _reference_spec("spec_fresnel_gradient", shape, seed, sm, **kwargs)


for _fn in (
    ricky_viper_pit_hex,
    ricky_wave_ripple,
    ricky_samhain_ritual,
    ricky_ouija_mystic,
    ricky_stardust_fine,
    ricky_spec_terrain_erosion,
    ricky_spec_stress_fractures,
    ricky_spec_snake_scales,
    ricky_spec_liquid_metal,
    ricky_spec_fresnel_gradient,
):
    _fn._spb_concept_complete = True
