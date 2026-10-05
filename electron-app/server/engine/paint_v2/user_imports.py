"""USER IMPORTS — persistent local image-authored finishes (paint monolithics first).

Storage: ``SPB_USER_IMPORTS_DIR`` or ``%APPDATA%/ShokkerPaintBooth/user_imports/``.
Separate from Guest Designers (shipped) and Finish Mixer ``custom_*`` recipes.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from engine.paint_v2.cultural_grunge_fun import (
    _post_adjust_viva_mexico_spec,
    _pre_adjust_viva_mexico_spec,
)
from engine.paint_v2.cultural_placement import apply_zone_placement_rgb, apply_zone_placement_spec
from engine.paint_v2.cultural_viva_mexico import (
    _mask2,
    _resize,
    _shape2,
    _viva_mexico_paint_luma_edge,
)
from engine.paint_v2.user_imports_ingest import entry_spec_channel_strengths
from engine.paint_v2.user_imports_paths import CATEGORY_NAME, ID_PREFIX, user_imports_root
from engine.spec_sculpt.fracture import fracture_spec

_USER_MONOLITHICS: Dict[str, Tuple] = {}
_USER_PATTERNS: Dict[str, Dict[str, Any]] = {}
_USER_SPEC_OVERLAYS: Dict[str, Any] = {}
_CATALOG: List[Dict[str, Any]] = []
_BOUNDED_COMBINED_SPEC_IDS = None


def _load_manifest() -> dict:
    root = user_imports_root()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "manifest.json"
    if not path.exists():
        data = {"schema_version": 1, "category": CATEGORY_NAME, "entries": []}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": 1, "category": CATEGORY_NAME, "entries": []}


def get_catalog_entries() -> List[Dict[str, Any]]:
    return list(_CATALOG)


def get_finish_ids() -> List[str]:
    return [e["id"] for e in _CATALOG if e.get("kind") == "paint_monolithic"]


def get_pattern_ids() -> List[str]:
    return [e["id"] for e in _CATALOG if e.get("kind") == "pattern"]


def get_spec_overlay_ids() -> List[str]:
    return [e["id"] for e in _CATALOG if e.get("kind") == "spec_overlay"]


def _entry_meta(finish_id: str) -> Dict[str, Any]:
    for entry in _CATALOG:
        if entry.get("id") == finish_id:
            return entry
    raise KeyError(finish_id)


def _asset_path(finish_id: str, suffix: str = "") -> Path:
    return user_imports_root() / f"{finish_id}{suffix}.png"


def _pattern_asset_path(finish_id: str) -> Path:
    return user_imports_root() / f"{finish_id}_pattern.png"


def _spec_overlay_asset_path(finish_id: str) -> Path:
    return user_imports_root() / f"{finish_id}_spec_overlay.png"


@lru_cache(maxsize=64)
def _load_rgb_cached(finish_id: str, mtime_ns: int) -> np.ndarray:
    path = _asset_path(finish_id)
    if not path.exists():
        raise FileNotFoundError(path)
    img = Image.open(path).convert("RGB")
    return (np.asarray(img, dtype=np.float32) / 255.0).astype(np.float32)


def _load_rgb(finish_id: str) -> np.ndarray:
    path = _asset_path(finish_id)
    return _load_rgb_cached(finish_id, path.stat().st_mtime_ns)


@lru_cache(maxsize=64)
def _load_spec_cached(finish_id: str, mtime_ns: int) -> np.ndarray:
    path = _asset_path(finish_id, "_spec")
    if not path.exists():
        raise FileNotFoundError(path)
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def _load_spec_rgba(finish_id: str) -> np.ndarray:
    path = _asset_path(finish_id, "_spec")
    return _load_spec_cached(finish_id, path.stat().st_mtime_ns)


@lru_cache(maxsize=64)
def _load_gray_cached(path_str: str, mtime_ns: int) -> np.ndarray:
    path = Path(path_str)
    img = Image.open(path).convert("L")
    return (np.asarray(img, dtype=np.float32) / 255.0).astype(np.float32)


def _load_gray(path: Path) -> np.ndarray:
    return _load_gray_cached(str(path), path.stat().st_mtime_ns)


def _paint_from_asset(finish_id: str, paint, shape, mask, pm: float) -> np.ndarray:
    h, w = _shape2(shape)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    tex = apply_zone_placement_rgb(tex, (h, w), mask=mask)
    m3 = _mask2(mask, (h, w))[:, :, None]
    strength = np.clip(float(pm) * 0.98, 0.0, 1.0)
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - m3 * strength) + tex[:, :, :3] * (m3 * strength)
    return np.clip(paint, 0.0, 1.0).astype(np.float32)


def _spec_from_dna_plate(finish_id: str, shape, mask, sm: float) -> np.ndarray:
    """Apply baked DNA spec as-is (Try in Booth / World staging).

    Skips Viva pre/post passes that re-tune spec against the finish *paint* PNG —
    that file is the SHOKK DROP upload, not the truck zone paint, which caused
    World thumbnails to disagree with Paint Booth renders.
    """
    h, w = _shape2(shape)
    spec = _resize(_load_spec_rgba(finish_id), (h, w), cv2.INTER_AREA).astype(np.float32)
    spec = apply_zone_placement_spec(spec, (h, w), mask=mask)
    m = _mask2(mask, (h, w))
    outside = 1.0 - m
    # [SPB SHOKK DROP authored verbatim 2026-06-16 — owner: "the channels I upload in SHOKK DROP must
    # render EXACTLY, no quarter"] A `authored_set` finish (the user's EXACT uploaded M/R/Cc plate)
    # must pass through BYTE-IDENTICAL inside the painted region. The dna_plate math below scales the
    # channels by `sm * m` AND floors roughness at 15 — so an authored roughness of 0 (or any value
    # < 15) was bumped to 15, a black clearcoat picked up a 16 fill at AA edges, etc. (Root cause of
    # the "slight change" bug.) For authored specs we lay the channels down VERBATIM where the mask is
    # fully inside (no floor, no sm/m down-scale), blending only the benign outside fill weighted by
    # `outside` so fully-inside pixels (outside==0) keep the EXACT uploaded byte. dna_plate / World-
    # staging finishes are unaffected — they still get the original floored/filled behavior below.
    if is_authored_spec(finish_id):
        spec[:, :, 0] = np.clip(spec[:, :, 0] * m + 4.0 * outside, 0, 255)
        spec[:, :, 1] = np.clip(spec[:, :, 1] * m + 120.0 * outside, 0, 255)
        spec[:, :, 2] = np.clip(spec[:, :, 2] * m + 16.0 * outside, 0, 255)
        spec[:, :, 3] = 255
        return spec.astype(np.uint8)
    spec[:, :, 0] = np.clip(spec[:, :, 0] * sm * m + 4.0 * outside, 0, 255)
    spec[:, :, 1] = np.clip(spec[:, :, 1] * sm * m + 120.0 * outside, 15, 255)
    spec[:, :, 2] = np.clip(spec[:, :, 2] * sm * m + 16.0 * outside, 0, 255)
    spec[:, :, 3] = 255
    return spec.astype(np.uint8)


def _spec_from_fracture(finish_id: str, shape, mask, sm: float) -> np.ndarray:
    """FRACTURE auto-derive — ignite the user's OWN paint with the FRACTURED look.

    [SPB FRACTURE auto-derive 2026-06-16 — owner: the "drop-a-paint -> FRACTURE the spec"
    path] Instead of the Viva-polish auto-DNA bake (_spec_from_combined), trace the paint's
    own edges/graphics and apply the FRACTURED ignition relationship (near-chrome M~252,
    maxed clearcoat Cc~255, roughness woven ~30-140 along the motif lanes). The PAINT supplies
    the dark albedo; the SPEC supplies the angle-gated ignition. Mask-aware: outside the
    painted region the shared engine lays the calm inv-mask fill (M~4 / R~120 / Cc~16), so this
    matches the (M, R, Cc, A) uint8 spec contract the other spec fns return.
    """
    h, w = _shape2(shape)
    m = _mask2(mask, (h, w))
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    tex = apply_zone_placement_rgb(tex, (h, w), mask=m)
    spec = fracture_spec(tex, m, as_uint8=True)
    spec = apply_zone_placement_spec(spec.astype(np.float32), (h, w), mask=m)
    spec[:, :, 3] = 255
    return spec.astype(np.uint8)


def _spec_from_combined(finish_id: str, shape, mask, sm: float) -> np.ndarray:
    h, w = _shape2(shape)
    m = _mask2(mask, (h, w))
    if _BOUNDED_COMBINED_SPEC_IDS is None and max(h, w) > 1024:
        # SPB paint-finish perf loop 2026-05-31; owner: "Speed is king in this app."
        # Black Rainbow Holo X2 measured 6170.7ms -> 2202.7ms; bound auto-DNA spec polish
        # while keeping the imported paint plate full-size.
        scale = 1024.0 / float(max(h, w))
        sh = max(256, int(round(h * scale)))
        sw = max(256, int(round(w * scale)))
        m_small = cv2.resize(m, (sw, sh), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        outside_small = 1.0 - m_small
        spec = _resize(_load_spec_rgba(finish_id), (sh, sw), cv2.INTER_AREA).astype(np.float32)
        spec = apply_zone_placement_spec(spec, (sh, sw), mask=m_small)
        tex = _resize(_load_rgb(finish_id), (sh, sw), cv2.INTER_AREA)
        tex = apply_zone_placement_rgb(tex, (sh, sw), mask=m_small)

        _pre_adjust_viva_mexico_spec(spec, tex, m_small, finish_id)
        spec[:, :, 0] = np.clip(spec[:, :, 0] * sm * m_small + 4.0 * outside_small, 0, 255)
        spec[:, :, 1] = np.clip(spec[:, :, 1] * sm * m_small + 120.0 * outside_small, 15, 255)
        spec[:, :, 2] = np.clip(spec[:, :, 2] * sm * m_small + 16.0 * outside_small, 0, 255)
        spec[:, :, 3] = 255
        out = _post_adjust_viva_mexico_spec(spec.astype(np.uint8), tex, m_small).astype(np.float32)
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        outside = 1.0 - m
        out[:, :, 0] = np.clip(out[:, :, 0] * m + 4.0 * outside, 0, 255)
        out[:, :, 1] = np.clip(out[:, :, 1] * m + 120.0 * outside, 15, 255)
        out[:, :, 2] = np.clip(out[:, :, 2] * m + 16.0 * outside, 0, 255)
        out[:, :, 3] = 255
        return out.astype(np.uint8)

    spec = _resize(_load_spec_rgba(finish_id), (h, w), cv2.INTER_AREA).astype(np.float32)
    spec = apply_zone_placement_spec(spec, (h, w), mask=mask)
    outside = 1.0 - m
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    tex = apply_zone_placement_rgb(tex, (h, w), mask=mask)
    _pre_adjust_viva_mexico_spec(spec, tex, m, finish_id)
    spec[:, :, 0] = np.clip(spec[:, :, 0] * sm * m + 4.0 * outside, 0, 255)
    spec[:, :, 1] = np.clip(spec[:, :, 1] * sm * m + 120.0 * outside, 15, 255)
    spec[:, :, 2] = np.clip(spec[:, :, 2] * sm * m + 16.0 * outside, 0, 255)
    spec[:, :, 3] = 255
    return _post_adjust_viva_mexico_spec(spec.astype(np.uint8), tex, m)


def _spec_from_metallic_roughness(finish_id: str, shape, mask, sm: float) -> np.ndarray:
    meta = _entry_meta(finish_id)
    h, w = _shape2(shape)
    m_hw = _mask2(mask, (h, w))
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    m_map = _resize(_load_gray(_asset_path(finish_id, "_metallic")), (h, w), cv2.INTER_AREA)
    r_map = _resize(_load_gray(_asset_path(finish_id, "_roughness")), (h, w), cv2.INTER_AREA)
    if meta.get("invert_roughness"):
        r_map = 1.0 - r_map
    outside = 1.0 - m_hw
    M = np.clip(m_map * 255.0 * float(sm) * m_hw + 4.0 * outside, 0.0, 255.0)
    R = np.clip(r_map * 255.0 * m_hw + 120.0 * outside, 15.0, 255.0)
    gray, edge_n = _viva_mexico_paint_luma_edge(tex, m_hw)
    dark = gray < (34.0 / 255.0)
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


def _make_paint_fn(finish_id: str, entry: Dict[str, Any]):
    from engine.core import paint_none

    # SPB-109 World staging: dna_plate spec + use_paint_source applies SHOKK DROP as zone paint.
    paint_off = bool(entry.get("staged_booth"))
    if entry.get("spec_mode") == "dna_plate" and not entry.get("use_paint_source"):
        paint_off = True
    if paint_off:
        paint_fn = paint_none
        paint_fn.__name__ = f"paint_{finish_id}_noop"
        return paint_fn

    def paint_fn(paint, shape, mask, seed, pm, bb):
        return _paint_from_asset(finish_id, paint, shape, mask, pm)

    paint_fn.__name__ = f"paint_{finish_id}"
    return paint_fn


def _make_spec_fn(finish_id: str, spec_mode: str):
    def spec_fn(shape, mask, seed, sm):
        if spec_mode == "metallic_roughness":
            return _spec_from_metallic_roughness(finish_id, shape, mask, sm)
        # [SPB FRACTURE auto-derive 2026-06-16] "fractured" = the user dropped ONLY a paint and
        # chose "FRACTURE the spec". Ignite their paint with the FRACTURED look (traces the paint's
        # own geometry, near-chrome M, maxed clearcoat, woven roughness) instead of the auto-DNA bake.
        if spec_mode == "fractured":
            return _spec_from_fracture(finish_id, shape, mask, sm)
        # [SPB SHOKK DROP authored-spec fix 2026-06-06 — owner: "the R/G/B channels IGNORE what I
        # uploaded in SHOKK DROP"] "authored_set" = the user supplied EXACT spec channels (a combined
        # RGB plate, separate M/R plates, or separate R/G/B channel plates = channel_split). It MUST
        # render VERBATIM. Route it through the same as-is loader as dna_plate, which SKIPS the
        # Viva-Mexico pre/post spec polish. The old code let authored_set fall through to
        # _spec_from_combined, whose _pre/_post_adjust_viva_mexico_spec RE-TUNE the spec against the
        # PAINT texture — injecting procedural metallic/roughness that OVERWROTE the user's
        # black-R / gray-G channels (verified: ui_bjeans1_spec.png holds R~0,G~136,B~0 but SPB showed
        # red/green procedural noise). _spec_from_dna_plate applies the authored channels as-is.
        if spec_mode in ("dna_plate", "authored_set"):
            return _spec_from_dna_plate(finish_id, shape, mask, sm)
        return _spec_from_combined(finish_id, shape, mask, sm)

    spec_fn.__name__ = f"spec_{finish_id}"
    # [SPB authored-spec verbatim 2026-06-07] Tag the spec mode so the engine (shokker_engine_v2
    # monolithic path) can render an authored_set spec VERBATIM — i.e. NOT scale it by the zone's
    # base_spec_strength slider. Owner-verified: an authored roughness 136 was exporting as 237
    # (= 136 * base_spec_strength 2.0) when the finish was used as a zone BASE.
    spec_fn.__spec_mode__ = spec_mode
    return spec_fn


def _clear_caches() -> None:
    _load_rgb_cached.cache_clear()
    _load_spec_cached.cache_clear()
    _load_gray_cached.cache_clear()


@lru_cache(maxsize=32)
def _load_spec_overlay_cached(finish_id: str, mtime_ns: int) -> np.ndarray:
    path = _spec_overlay_asset_path(finish_id)
    if not path.exists():
        raise FileNotFoundError(path)
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def _load_spec_overlay_rgba(finish_id: str) -> np.ndarray:
    path = _spec_overlay_asset_path(finish_id)
    return _load_spec_overlay_cached(finish_id, path.stat().st_mtime_ns)


def _make_spec_overlay_fn(finish_id: str, strengths: Optional[Dict[str, float]] = None):
    """Spec stack overlay from authored RGBA plate — full M/R/CC channels."""

    m_str = float((strengths or {}).get("M", 1.0))
    r_str = float((strengths or {}).get("R", 1.0))
    c_str = float((strengths or {}).get("C", (strengths or {}).get("Cc", 1.0)))

    def spec_fn(shape, seed, sm, **kwargs):
        h, w = _shape2(shape)
        spec = _resize(_load_spec_overlay_rgba(finish_id), (h, w), cv2.INTER_AREA).astype(np.float32)
        m = np.clip(spec[:, :, 0] / 255.0 * m_str, 0.0, 1.0)
        r = np.clip(spec[:, :, 1] / 255.0 * r_str, 0.0, 1.0)
        cc = np.clip(spec[:, :, 2] / 255.0 * c_str, 0.0, 1.0)
        out = np.stack([m, r, cc], axis=-1).astype(np.float32)
        if sm != 1.0:
            out = out * float(sm) + 0.5 * (1.0 - float(sm))
        return np.clip(out, 0.0, 1.0).astype(np.float32)

    spec_fn.__name__ = f"spec_overlay_{finish_id}"
    spec_fn.__doc__ = (
        f"User import spec overlay ({finish_id}). "
        "Targets R=Metallic G=Roughness B=Clearcoat from authored RGB plate."
    )
    return spec_fn


def _build_pattern_entry(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    from engine.spec_paint import paint_none

    fid = entry["id"]
    path = _pattern_asset_path(fid)
    if not path.exists():
        return None
    abs_path = str(path.resolve()).replace("\\", "/")
    return {
        "image_path": abs_path,
        "paint_fn": paint_none,
        "desc": f"User import pattern: {entry.get('name', fid)}",
    }


# [SPB authored-spec verbatim 2026-06-07 v2] IDs of user-import finishes whose spec is the user's
# EXACT uploaded channels (spec_mode == "authored_set"). Tracked BY ID because the monolithic-
# contract wrappers (shokker_engine_v2 ~15452) strip custom function attributes, so a `__spec_mode__`
# tag set on the spec_fn never survives to the registered/wrapped fn. An id-set is wrapper-proof.
_AUTHORED_SPEC_IDS: set = set()


def is_authored_spec(finish_id) -> bool:
    """True if finish_id is a SHOKK DROP authored_set spec that must render VERBATIM (ignoring the
    base_spec_strength slider). Checked by ID, independent of any spec_fn wrapping."""
    return finish_id in _AUTHORED_SPEC_IDS


def reload_user_imports() -> Dict[str, Tuple]:
    """Rescan manifest + files; rebuild runtime registries."""
    global _USER_MONOLITHICS, _USER_PATTERNS, _USER_SPEC_OVERLAYS, _CATALOG, _AUTHORED_SPEC_IDS
    _clear_caches()
    _load_spec_overlay_cached.cache_clear()
    manifest = _load_manifest()
    catalog: List[Dict[str, Any]] = []
    monolithics: Dict[str, Tuple] = {}
    patterns: Dict[str, Dict[str, Any]] = {}
    spec_overlays: Dict[str, Any] = {}
    authored_ids: set = set()
    for entry in manifest.get("entries", []):
        fid = entry.get("id")
        kind = entry.get("kind", "paint_monolithic")
        if not fid or not str(fid).startswith(ID_PREFIX):
            continue
        if kind == "pattern":
            pat = _build_pattern_entry(entry)
            if pat:
                patterns[fid] = pat
                catalog.append(entry)
            continue
        if kind == "spec_overlay":
            if not _spec_overlay_asset_path(fid).exists():
                continue
            strengths = entry_spec_channel_strengths(entry)
            spec_overlays[fid] = _make_spec_overlay_fn(fid, strengths)
            catalog.append(entry)
            continue
        if not _asset_path(fid).exists():
            continue
        spec_mode = entry.get("spec_mode", "auto")
        if spec_mode == "metallic_roughness":
            if not _asset_path(fid, "_metallic").exists() or not _asset_path(fid, "_roughness").exists():
                continue
        elif spec_mode == "fractured":
            # [SHOKK DROP loop 2026-08-09 — FRACTURE revival] "FRACTURE the spec"
            # imports intentionally bake NO _spec.png: import_paint_files(fracture=True)
            # only tags spec_mode="fractured" and _make_spec_fn derives the spec from
            # the paint plate at render time via _spec_from_fracture(). This gate used
            # to fall through to the generic `_spec.png` requirement below and skip
            # every such entry, so the feature had been silently dead since it shipped
            # 2026-06-16 — the owner's own ui_mag01_2 (2026-06-19) vanished this way.
            # The paint plate (checked above) is the only file this mode needs.
            # Verified: _spec_from_fracture @2048² = 1.29s, M~247 / R 30-78 / Cc 255,
            # matching the values its own docstring documents.
            pass
        elif not _asset_path(fid, "_spec").exists():
            continue
        monolithics[fid] = (_make_spec_fn(fid, spec_mode), _make_paint_fn(fid, entry))
        if spec_mode == "authored_set":
            authored_ids.add(fid)
        catalog.append(entry)
    _USER_MONOLITHICS = monolithics
    _USER_PATTERNS = patterns
    _USER_SPEC_OVERLAYS = spec_overlays
    _CATALOG = catalog
    _AUTHORED_SPEC_IDS = authored_ids
    return monolithics


def _purge_ui_keys(reg: dict) -> None:
    for key in list(reg.keys()):
        if str(key).startswith(ID_PREFIX):
            del reg[key]


def register_user_imports(mono_reg: dict, pattern_reg: Optional[dict] = None) -> int:
    reload_user_imports()
    mono_reg.update(_USER_MONOLITHICS)
    if pattern_reg is not None:
        _purge_ui_keys(pattern_reg)
        pattern_reg.update(_USER_PATTERNS)
    try:
        from engine import spec_patterns as _sp

        _purge_ui_keys(_sp.PATTERN_CATALOG)
        _sp.PATTERN_CATALOG.update(_USER_SPEC_OVERLAYS)
    except Exception:
        pass
    return len(_USER_MONOLITHICS) + len(_USER_PATTERNS) + len(_USER_SPEC_OVERLAYS)


def sync_registry(mono_reg: dict, pattern_reg: Optional[dict] = None) -> int:
    """Replace all ``ui_*`` entries after import/delete."""
    _purge_ui_keys(mono_reg)
    if pattern_reg is not None:
        _purge_ui_keys(pattern_reg)
    try:
        from engine import spec_patterns as _sp

        _purge_ui_keys(_sp.PATTERN_CATALOG)
    except Exception:
        pass
    reload_user_imports()
    mono_reg.update(_USER_MONOLITHICS)
    if pattern_reg is not None:
        pattern_reg.update(_USER_PATTERNS)
    try:
        from engine import spec_patterns as _sp

        _sp.PATTERN_CATALOG.update(_USER_SPEC_OVERLAYS)
    except Exception:
        pass
    return len(_USER_MONOLITHICS) + len(_USER_PATTERNS) + len(_USER_SPEC_OVERLAYS)
