"""Guest Designers — image-authored monolithic finishes from external painters.

Each designer folder lives under ``assets/reference_textures/guest_designers/<key>/``
with a ``manifest.json`` listing finishes. Per finish, SPB expects:

- ``{id}.png`` — RGB albedo / design plate (same role as Cultural packs).
- ``{id}_metallic.png`` — grayscale **metallic** weight (white = strong metal → M channel).
- ``{id}_roughness.png`` — grayscale **roughness** (white = rough surface → R channel).

Clearcoat (Cc) is **not** taken from a third file by default; it is derived from the
albedo (luma + edges) so graphics still get wet holo highlights without hand-painting Cc.

Optional per-finish flags in manifest:

- ``invert_roughness``: if true, roughness is treated as glossiness (1 - sample).

Maps are resized to the render resolution and masked like Viva Mexico; the same
DNA void / ridge post-pass as Cultural finishes keeps black fields from blowing out metallic.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image

from engine.paint_v2.cultural_viva_mexico import (
    _post_adjust_viva_mexico_spec,
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
_GUEST_ROOT = Path(_rrd("guest_designers"))


def _load_designer_finishes() -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
    """Scan designer subfolders for manifest.json; return ids and meta per id."""
    ids: List[str] = []
    meta: Dict[str, Dict[str, Any]] = {}
    if not _GUEST_ROOT.is_dir():
        return ids, meta
    for sub in sorted(_GUEST_ROOT.iterdir()):
        if not sub.is_dir():
            continue
        man_path = sub / "manifest.json"
        if not man_path.exists():
            continue
        try:
            data = json.loads(man_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        designer_key = sub.name
        designer_display = data.get("designer_display_name") or designer_key.replace("_", " ").title()
        for item in data.get("finishes", []):
            fid = item.get("id")
            if not fid:
                continue
            ids.append(fid)
            entry = dict(item)
            entry["_designer_key"] = designer_key
            entry["_designer_display_name"] = designer_display
            entry["_asset_dir"] = sub
            meta[fid] = entry
    return ids, meta


_FINISH_IDS, _FINISH_META = _load_designer_finishes()


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


def _resize(arr: np.ndarray, shape, interpolation: int) -> np.ndarray:
    h, w = _shape2(shape)
    if arr.shape[:2] == (h, w):
        return arr
    return cv2.resize(arr, (w, h), interpolation=interpolation)


@lru_cache(maxsize=64)
def _load_rgb_cached(finish_id: str, mtime_ns: int) -> np.ndarray:
    meta = _FINISH_META.get(finish_id)
    if not meta:
        raise KeyError(f"Unknown guest designer finish: {finish_id}")
    path = meta["_asset_dir"] / f"{finish_id}.png"
    if not path.exists():
        raise FileNotFoundError(f"Missing guest albedo: {path}")
    img = Image.open(path).convert("RGB")
    return (np.asarray(img, dtype=np.float32) / 255.0).astype(np.float32)


def _load_rgb(finish_id: str) -> np.ndarray:
    meta = _FINISH_META[finish_id]
    path = meta["_asset_dir"] / f"{finish_id}.png"
    return _load_rgb_cached(finish_id, path.stat().st_mtime_ns)


@lru_cache(maxsize=64)
def _load_gray_cached(path_str: str, mtime_ns: int) -> np.ndarray:
    path = Path(path_str)
    img = Image.open(path).convert("L")
    return (np.asarray(img, dtype=np.float32) / 255.0).astype(np.float32)


def _load_gray_path(path: Path) -> np.ndarray:
    return _load_gray_cached(str(path), path.stat().st_mtime_ns)


def _paint_from_asset(finish_id: str, paint, shape, mask, pm: float) -> np.ndarray:
    h, w = _shape2(shape)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    m3 = _mask2(mask, (h, w))[:, :, None]
    strength = np.clip(float(pm) * 0.98, 0.0, 1.0)
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - m3 * strength) + tex[:, :, :3] * (m3 * strength)
    return np.clip(paint, 0.0, 1.0).astype(np.float32)


def _spec_from_author_maps(finish_id: str, shape, mask, sm: float) -> np.ndarray:
    """Build M/R from metallic & roughness grayscale; Cc from albedo structure."""
    meta = _FINISH_META[finish_id]
    asset_dir: Path = meta["_asset_dir"]
    h, w = _shape2(shape)
    m_hw = _mask2(mask, (h, w))

    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    m_map = _resize(
        _load_gray_path(asset_dir / f"{finish_id}_metallic.png"),
        (h, w),
        cv2.INTER_AREA,
    )
    r_map = _resize(
        _load_gray_path(asset_dir / f"{finish_id}_roughness.png"),
        (h, w),
        cv2.INTER_AREA,
    )
    if meta.get("invert_roughness"):
        r_map = 1.0 - r_map

    outside = 1.0 - m_hw

    # iRacing-style maps → SPB M (metallic) and R (roughness), scaled like Viva Mexico passes.
    M = np.clip(m_map * 255.0 * float(sm) * m_hw + 4.0 * outside, 0.0, 255.0)
    R = np.clip(r_map * 255.0 * m_hw + 120.0 * outside, 15.0, 255.0)

    gray, edge_n = _viva_mexico_paint_luma_edge(tex, m_hw)
    dark = gray < (34.0 / 255.0)
    # Cc: push gloss on bright/holo ridges; keep flat blacks matte (DNA-friendly).
    Cc = (
        10.0
        + (1.0 - dark.astype(np.float32)) * (8.0 + np.clip(gray, 0.0, 1.0) * 55.0)
        + edge_n * 42.0
        + np.clip(gray - 0.25, 0.0, 0.75) * 70.0 * m_map
    )
    Cc = np.clip(Cc * m_hw + 88.0 * outside, 8.0, 255.0)

    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:, :, 0] = M.astype(np.uint8)
    spec[:, :, 1] = R.astype(np.uint8)
    spec[:, :, 2] = Cc.astype(np.uint8)
    spec[:, :, 3] = 255
    return _post_adjust_viva_mexico_spec(spec, tex, m_hw)


def _make_paint_fn(finish_id: str):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        return _paint_from_asset(finish_id, paint, shape, mask, pm)

    paint_fn.__name__ = f"paint_{finish_id}"
    return paint_fn


def _make_spec_fn(finish_id: str):
    def spec_fn(shape, mask, seed, sm):
        return _spec_from_author_maps(finish_id, shape, mask, sm)

    spec_fn.__name__ = f"spec_{finish_id}"
    return spec_fn


GUEST_DESIGNER_MONOLITHICS = {
    fid: (_make_spec_fn(fid), _make_paint_fn(fid)) for fid in _FINISH_IDS
}


def get_catalog_for_picker() -> List[Dict[str, Any]]:
    """Frontend picker entries grouped under Guest Designer · <studio name>."""
    entries: List[Dict[str, Any]] = []
    for fid in _FINISH_IDS:
        meta = _FINISH_META.get(fid) or {}
        studio = str(meta.get("_designer_display_name") or "Guest Designer").strip()
        group = f"Guest Designer · {studio}"
        entries.append(
            {
                "id": fid,
                "name": meta.get("display_name") or fid,
                "desc": meta.get("description") or "Guest-authored paint + metallic + roughness plates.",
                "group": group,
                "swatch": "#4a5568",
                "tags": ["guest-designer", f"guest-{meta.get('_designer_key', 'designer')}"],
            }
        )
    return entries
