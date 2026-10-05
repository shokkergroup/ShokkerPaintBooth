"""Cultural / GRUNGE & FUN — image-authored paint + Viva Mexico spec polish.

Paint: assets/reference_textures/grunge_fun/{id}.png (2048)
Spec:  assets/reference_textures/grunge_fun/{id}_spec.png (baked M/R/Cc, enhanced at render)

See VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md and scripts/build_cultural_grunge_fun.py.
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
from engine.paint_v2.cultural_viva_mexico import (
    _finish_rng_seed,
    _mask2,
    _post_adjust_viva_mexico_spec,
    _pre_adjust_viva_mexico_spec,
    _resize,
    _shape2,
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
_ASSET_DIR = Path(_rrd("grunge_fun"))
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


_FALLBACK_FINISH_IDS = ("gf_halftone_hex_burst",)


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
_BOUNDED_SPEC_IDS = set(_FINISH_IDS)

# SPB perf (grunge_fun 2026-06-13): constants for the fused outside-fill boundary
# fixup. The final 2048 boundary pass used to do 3 separate strided per-channel
# clip-multiply-adds (~1.36s @2048, measured). Folding them into one contiguous
# broadcast op (out*m + const*outside, then a single per-channel np.clip via the
# LO/HI bound arrays) is bit-identical (verified maxdelta=0 on ones/soft/partial
# masks) and ~1.32x faster on that stage. CONST/LO/HI rows = M, R, Cc, A and
# match the long-standing per-channel constants (4/120/80 fill, [0/15/16,255] clip).
_SPEC_FILL_CONST = np.array([4.0, 120.0, 80.0, 0.0], dtype=np.float32)
_SPEC_CLIP_LO = np.array([0.0, 15.0, 16.0, 0.0], dtype=np.float32)
_SPEC_CLIP_HI = np.array([255.0, 255.0, 255.0, 255.0], dtype=np.float32)


@lru_cache(maxsize=128)
def _load_rgb_cached(finish_id, mtime_ns):
    path = _texture_path(finish_id)
    if not path.exists():
        raise FileNotFoundError(f"Missing Grunge & Fun texture: {path}")
    img = Image.open(path).convert("RGB")
    return (np.asarray(img, dtype=np.float32) / 255.0).astype(np.float32)


def _load_rgb(finish_id):
    path = _texture_path(finish_id)
    return _load_rgb_cached(finish_id, path.stat().st_mtime_ns)


@lru_cache(maxsize=128)
def _load_spec_cached(finish_id, mtime_ns):
    path = _spec_texture_path(finish_id)
    if not path.exists():
        raise FileNotFoundError(f"Missing Grunge & Fun spec map: {path}")
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def _load_spec(finish_id):
    path = _spec_texture_path(finish_id)
    return _load_spec_cached(finish_id, path.stat().st_mtime_ns)


def _paint_from_asset(finish_id, paint, shape, mask, pm):
    h, w = _shape2(shape)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    tex = apply_zone_placement_rgb(tex, (h, w), mask=mask)
    m3 = _mask2(mask, (h, w))[:, :, None]
    strength = np.clip(float(pm) * 0.98, 0.0, 1.0)
    # SPB perf (grunge_fun 2026-06-13): the alpha weight ``m3 * strength`` was
    # computed twice (once for the keep term, once for the paint-in term). Fold it
    # once into ``w`` — same float ops, bit-identical output (verified
    # np.array_equal across ones/soft/partial masks, pm in {1.0,0.6}), one fewer
    # full HxWx1 multiply. Image-plate family; heavy spec polish is in
    # cultural_viva_mexico._pre_adjust (out-of-lane) and bounds the total.
    w_alpha = m3 * strength
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - w_alpha) + tex[:, :, :3] * w_alpha
    return np.clip(paint, 0.0, 1.0).astype(np.float32)


def _spec_from_asset(finish_id, shape, mask, sm):
    h, w = _shape2(shape)
    m = _mask2(mask, (h, w))
    if finish_id in _BOUNDED_SPEC_IDS and max(h, w) > 1024:
        # SPB paint-finish perf loop 2026-05-31; owner: "Speed is king in this app."
        # Slow Grunge rows measured 5.73-6.03s -> 1.81-1.82s; bounded spec polish preserves
        # the authored paint plate while cutting full-res polish math.
        scale = 1024.0 / float(max(h, w))
        sh = max(256, int(round(h * scale)))
        sw = max(256, int(round(w * scale)))
        m_small = cv2.resize(m, (sw, sh), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        outside_small = 1.0 - m_small
        spec = _resize(_load_spec(finish_id), (sh, sw), cv2.INTER_AREA).astype(np.float32)
        spec = apply_zone_placement_spec(spec, (sh, sw), mask=m_small)
        tex = _resize(_load_rgb(finish_id), (sh, sw), cv2.INTER_AREA)
        tex = apply_zone_placement_rgb(tex, (sh, sw), mask=m_small)

        _pre_adjust_viva_mexico_spec(spec, tex, m_small, finish_id)
        spec[:, :, 0] = np.clip(spec[:, :, 0] * sm * m_small + 4.0 * outside_small, 0, 255)
        spec[:, :, 1] = np.clip(spec[:, :, 1] * m_small + 120.0 * outside_small, 15, 255)
        spec[:, :, 2] = np.clip(spec[:, :, 2] * m_small + 80.0 * outside_small, 16, 255)
        spec[:, :, 3] = 255
        out = _post_adjust_viva_mexico_spec(spec.astype(np.uint8), tex, m_small).astype(np.float32)
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        # Fused outside-fill: one contiguous HxWx4 broadcast (out*m + const*outside)
        # + one per-channel clip, replacing 3 strided per-channel passes.
        # Bit-identical to the old 3-clip block (verified). ~1.32x on this stage.
        outside = 1.0 - m
        out *= m[:, :, None]
        out += _SPEC_FILL_CONST * outside[:, :, None]
        np.clip(out, _SPEC_CLIP_LO, _SPEC_CLIP_HI, out=out)
        out[:, :, 3] = 255.0
        return out.astype(np.uint8)

    spec = _resize(_load_spec(finish_id), (h, w), cv2.INTER_AREA).astype(np.float32)
    spec = apply_zone_placement_spec(spec, (h, w), mask=mask)
    outside = 1.0 - m
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    # SPB-2026-05-18: spec scale must match paint plate — pre_adjust reads tex edges/chroma.
    tex = apply_zone_placement_rgb(tex, (h, w), mask=mask)
    _pre_adjust_viva_mexico_spec(spec, tex, m, finish_id)
    spec[:, :, 0] = np.clip(spec[:, :, 0] * sm * m + 4.0 * outside, 0, 255)
    spec[:, :, 1] = np.clip(spec[:, :, 1] * m + 120.0 * outside, 15, 255)
    spec[:, :, 2] = np.clip(spec[:, :, 2] * m + 80.0 * outside, 16, 255)
    spec[:, :, 3] = 255
    out = spec.astype(np.uint8)
    return _post_adjust_viva_mexico_spec(out, tex, m)


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


GRUNGE_FUN_MONOLITHICS = {
    finish_id: (_make_spec_fn(finish_id), _make_paint_fn(finish_id))
    for finish_id in _FINISH_IDS
}
