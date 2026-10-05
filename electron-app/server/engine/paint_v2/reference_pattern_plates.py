"""Reference Pattern Plates - real source images as Special finishes.

SPB owner 2026-05-30: implement the source folder
assets/patterns/spec_overlay_patterns as 2048 paint plates and paired dynamic
spec maps. Metric movement: first bake had several flat CC channels; builder
rebake raised all CC std >= 24.46 at 2048.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from engine.paint_v2.cultural_placement import apply_zone_placement_rgb, apply_zone_placement_spec


_REL_ASSET = Path("assets") / "reference_textures" / "pattern_plates"
_FALLBACK_FINISH_IDS = (
    "pp_holographic_oil_circuit",
    "pp_black_emboss_mandala",
    "pp_graphite_cross_lattice",
    "pp_marble_flow_pearl",
    "pp_acid_carbon_mesh",
    "pp_noir_houndstooth_star",
    "pp_hazard_chevron_weave",
    "pp_burn_hole_mesh",
    "pp_teal_hex_haze",
    "pp_shadow_diamond_mesh",
    "pp_talavera_tile_riot",
    "pp_green_plasma_vein",
    "pp_neon_fracture_net",
    "pp_pink_checker_carbon",
    "pp_red_herringbone_heat",
    "pp_chrome_oval_chain",
    "pp_terracotta_ceramic_grid",
    "pp_gunmetal_geo_tessellation",
    "pp_tokyo_script_textile",
    "pp_lime_pixel_confetti",
    "pp_psychedelic_floral_spin",
    "pp_ice_facet_shatter",
    "pp_ember_circuit_maze",
    "pp_blue_polygon_shatter",
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
        dl = Path(_rrd("pattern_plates"))
        if (dl / "manifest.json").exists():
            return dl
    except Exception:
        pass
    return here.parents[2] / _REL_ASSET


_ASSET_DIR = _resolve_asset_dir()


def _shape2(shape) -> tuple[int, int]:
    return tuple(shape[:2]) if len(shape) > 2 else tuple(shape)


def _mask2(mask, shape: tuple[int, int]) -> np.ndarray:
    h, w = shape
    if mask is None:
        return np.ones((h, w), dtype=np.float32)
    arr = np.asarray(mask, dtype=np.float32)
    if arr.shape[:2] != (h, w):
        arr = cv2.resize(arr, (w, h), interpolation=cv2.INTER_LINEAR)
    if arr.ndim == 3:
        arr = arr[:, :, 0]
    if arr.max() > 1.0:
        arr = arr / 255.0
    return np.clip(arr, 0.0, 1.0).astype(np.float32)


def _resize(arr: np.ndarray, shape: tuple[int, int], interp=cv2.INTER_AREA) -> np.ndarray:
    h, w = shape
    if arr.shape[:2] == (h, w):
        return arr.copy()
    return cv2.resize(arr, (w, h), interpolation=interp)


def _manifest_finish_ids() -> tuple[str, ...]:
    path = _ASSET_DIR / "manifest.json"
    if not path.exists():
        return _FALLBACK_FINISH_IDS
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ids = tuple(str(item["id"]) for item in data.get("finishes", []) if item.get("id"))
        return ids or _FALLBACK_FINISH_IDS
    except Exception:
        return _FALLBACK_FINISH_IDS


_FINISH_IDS = _manifest_finish_ids()


@lru_cache(maxsize=32)
def _load_rgb_cached(finish_id: str, mtime_ns: int) -> np.ndarray:
    del mtime_ns
    path = _ASSET_DIR / f"{finish_id}.png"
    if not path.exists():
        raise FileNotFoundError(f"Missing Reference Pattern Plate texture: {path}")
    return (np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0).astype(np.float32)


def _load_rgb(finish_id: str) -> np.ndarray:
    path = _ASSET_DIR / f"{finish_id}.png"
    return _load_rgb_cached(finish_id, path.stat().st_mtime_ns)


@lru_cache(maxsize=32)
def _load_spec_cached(finish_id: str, mtime_ns: int) -> np.ndarray:
    del mtime_ns
    path = _ASSET_DIR / f"{finish_id}_spec.png"
    if not path.exists():
        raise FileNotFoundError(f"Missing Reference Pattern Plate spec map: {path}")
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def _load_spec(finish_id: str) -> np.ndarray:
    path = _ASSET_DIR / f"{finish_id}_spec.png"
    return _load_spec_cached(finish_id, path.stat().st_mtime_ns)


def _paint_from_asset(finish_id: str, paint, shape, mask, pm):
    h, w = _shape2(shape)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    tex = apply_zone_placement_rgb(tex, (h, w), mask=mask)
    m = _mask2(mask, (h, w))[:, :, None]
    strength = np.clip(float(pm) * 0.98, 0.0, 1.0)
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - m * strength) + tex[:, :, :3] * (m * strength)
    return np.clip(paint, 0.0, 1.0).astype(np.float32)


def _spec_from_asset(finish_id: str, shape, mask, sm):
    h, w = _shape2(shape)
    spec = _resize(_load_spec(finish_id), (h, w), cv2.INTER_AREA).astype(np.float32)
    spec = apply_zone_placement_spec(spec, (h, w), mask=mask)
    m = _mask2(mask, (h, w))
    outside = 1.0 - m
    spec[:, :, 0] = np.clip(spec[:, :, 0] * float(sm) * m + 4.0 * outside, 0, 255)
    spec[:, :, 1] = np.clip(spec[:, :, 1] * m + 135.0 * outside, 8, 255)
    spec[:, :, 2] = np.clip(spec[:, :, 2] * m + 80.0 * outside, 8, 255)
    spec[:, :, 3] = 255
    return spec.astype(np.uint8)


def _make_paint_fn(finish_id: str):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        del seed, bb
        return _paint_from_asset(finish_id, paint, shape, mask, pm)

    paint_fn.__name__ = f"paint_{finish_id}"
    return paint_fn


def _make_spec_fn(finish_id: str):
    def spec_fn(shape, mask, seed, sm):
        del seed
        return _spec_from_asset(finish_id, shape, mask, sm)

    spec_fn.__name__ = f"spec_{finish_id}"
    return spec_fn


REFERENCE_PATTERN_PLATE_MONOLITHICS = {
    finish_id: (_make_spec_fn(finish_id), _make_paint_fn(finish_id))
    for finish_id in _FINISH_IDS
}
