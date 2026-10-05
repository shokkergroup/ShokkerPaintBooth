"""Cultural / FORBIDDEN DRAGON — image-authored dragon-brocade finishes.

Source art: dense Chinese imperial dragon BROCADES (edge-to-edge, hundreds of
small motifs — coiling dragons, scales, clouds, flames, pearls, coins), scaled
to the 2048 canvas by ``scripts/build_cultural_forbidden_dragon.py``. The dense,
fine, full-bleed art is what makes it wrap any car UV without a giant hero, and
it's the ideal substrate for the spec trace.

The M/R/CC spec is derived FROM the paint image at render time using the proven
Viva Mexico sculptor (gold -> metal, paint-chroma -> varied M/R/Cc triplets,
motif edges -> ridge relief, multi-octave micro-grit, highlight crests). That is
the 2026-05-28 spec-diversity breakthrough applied to TRACED cultural art: each
colour region becomes its own material microstate, so the scales / clouds /
flames catch light and shimmer ("breathe") on the car. Keeping the spec
runtime-derived means it is always in sync with the art and every new dragon is
a pure drop-in (no separate spec-plate bake).

Three-copy file (root, electron-app/server, electron-app/server/pyserver/_internal).
"""
from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from engine.core import multi_scale_noise
from engine.paint_v2.cultural_placement import apply_zone_placement_rgb

_ROOT = Path(__file__).resolve().parents[2]
try:
    from engine.asset_packs import resolve_ref_dir as _rrd
except Exception:
    try:
        from ..asset_packs import resolve_ref_dir as _rrd
    except Exception:
        _rrd = lambda r: str(_ROOT / "assets" / "reference_textures" / r)  # noqa: E731
# finish-pack-downloader 2026-06-07: route through resolver so a DOWNLOADED pack works for buyers
_ASSET_DIR = Path(_rrd("cultural/forbidden_dragon"))
_JPG_ASSET_DIR = _ASSET_DIR / "jpg_2048"

_FALLBACK_FINISH_IDS = (
    "fd_azure_celestial",
    "fd_vermilion_fire",
    "fd_abyssal_sea",
    "fd_imperial_gold",
    "fd_storm_black",
    "fd_jade_empress",
    "fd_frost_emperor",
    "fd_bronze_relic",
    "fd_pearl_chaser",
    "fd_dragon_phoenix",
)


def _prefer_jpg_runtime() -> bool:
    return os.environ.get("SPB_CULTURAL_USE_JPG", "1").lower() not in {"0", "false", "no"}


def _texture_path(finish_id: str) -> Path:
    jpg = _JPG_ASSET_DIR / f"{finish_id}.jpg"
    if _prefer_jpg_runtime() and jpg.exists():
        return jpg
    return _ASSET_DIR / f"{finish_id}.png"


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
    path = _texture_path(finish_id)
    if not path.exists():
        raise FileNotFoundError(f"Missing Forbidden Dragon texture: {path}")
    img = Image.open(path).convert("RGB")
    return (np.asarray(img, dtype=np.float32) / 255.0).astype(np.float32)


def _load_rgb(finish_id):
    path = _texture_path(finish_id)
    return _load_rgb_cached(finish_id, path.stat().st_mtime_ns)


def _finish_seed(finish_id: str) -> int:
    """Stable per-finish seed for the independent channel noise designs."""
    return int.from_bytes(hashlib.blake2s(finish_id.encode("utf-8"), digest_size=4).digest(), "big")


def _msc(h, w, scales, seed):
    """multi_scale_noise normalised to 0..1 (fine, near-pixel octaves)."""
    n = multi_scale_noise((h, w), list(scales), [0.5, 0.3, 0.2][: len(scales)], int(seed) & 0x7FFFFFFF)
    return ((np.asarray(n, dtype=np.float32) + 1.0) * 0.5).astype(np.float32)


def _dragon_spec_trace(tex, m, finish_id, sm):
    """Purpose-built dragon spec tracer (2026-05-28 doctrine — deliberately NOT
    the generic Viva sculptor):

      1. CLOISONNE PER-COLOUR MATERIAL — each colour cell of the art becomes its
         own material: gold linework -> bright glossy METAL, white/silver ->
         pearl, saturated cool/warm cells -> glossy lacquer, dark gaps -> matte
         void. This is the owner's "trace the scales one material, the fire
         another, cut out and distinct."
      2. DECORRELATED CHANNELS — M, R and CC each carry an INDEPENDENT fine
         design (different seeds + scales), gated onto the lit motifs, so the
         combined spec holds hundreds of distinct microstates and the colour
         shimmers / breathes on the car (the 0.0 -> 0.8 decorr breakthrough).
      3. GLOSS LEVER — motifs read glossy (low roughness = tight fast Fresnel =
         the flash that lifts off the car); the ground stays matte so the motifs
         pop. Gold OUTLINES get the hottest flash of all.
    """
    # PERF 2026-06-13 (cultural_forbidden_dragon lane): the math below is IDENTICAL
    # to the original cloisonné tracer; it has only been re-expressed in pure
    # float32 with fused / in-place numpy ops to halve memory bandwidth at 2048².
    # The original mixed float32 arrays with Python-float scalars, which silently
    # promoted every full-canvas intermediate to float64 (2× the bytes touched).
    # The uint8 spec output is bit-identical (verified array_equal on all 20 fd_*),
    # because any sub-LSB float32-vs-float64 difference rounds away in the cast.
    f32 = np.float32
    h, w = tex.shape[:2]
    r, g, b = tex[:, :, 0], tex[:, :, 1], tex[:, :, 2]
    L = f32(0.2126) * r + f32(0.7152) * g + f32(0.0722) * b
    # shared channel-max subexpressions (reused by S and the colour masks)
    max_rg = np.maximum(r, g)
    mx = np.maximum(max_rg, b)
    mn = np.minimum(np.minimum(r, g), b)
    S = (mx - mn) / (mx + f32(1e-6))

    gold = np.clip(np.minimum(r, g) - b, f32(0.0), f32(1.0))             # gold / amber
    warm = np.clip(r - np.maximum(g, b) * f32(0.9), f32(0.0), f32(1.0))  # red / orange
    cool = np.clip(b - max_rg * f32(0.9), f32(0.0), f32(1.0))            # blue
    green = np.clip(g - np.maximum(r, b) * f32(0.9), f32(0.0), f32(1.0))  # jade / green
    white = np.clip((L - f32(0.62)) / f32(0.38), f32(0.0), f32(1.0)) * (f32(1.0) - S)  # pearl / silver
    dark = np.clip((f32(0.20) - L) / f32(0.20), f32(0.0), f32(1.0))  # gaps / ground

    lap = cv2.Laplacian(L * f32(255.0), cv2.CV_32F, ksize=3)
    np.abs(lap, out=lap)
    edge = np.clip(lap / f32(float(np.percentile(lap, 98.0)) + 1e-6), f32(0.0), f32(1.0))

    # 1) cloisonné base material per colour cell. The accumulations below preserve
    # the original left-to-right evaluation order (so the result is bit-identical),
    # using np.add(..., out=) to drop the chained full-canvas temporaries.
    M = f32(28.0) + gold * f32(205.0)
    np.add(M, warm * f32(75.0), out=M)
    np.add(M, white * f32(120.0), out=M)
    np.add(M, green * f32(45.0), out=M)
    np.add(M, cool * f32(20.0), out=M)

    R = f32(70.0) + dark * f32(165.0)
    np.subtract(R, gold * f32(48.0), out=R)
    np.subtract(R, white * f32(42.0), out=R)
    np.subtract(R, (warm + cool + green) * f32(22.0), out=R)

    CC = f32(30.0) + S * f32(150.0)
    np.add(CC, gold * f32(55.0), out=CC)
    np.add(CC, white * f32(85.0), out=CC)
    np.subtract(CC, dark * f32(18.0), out=CC)

    # 2) three INDEPENDENT decorrelated micro-designs, gated onto lit motifs.
    # noise_term = ((noise - 0.5) * scale) * gate  (same order as original);
    # built in-place into a single scratch buffer per channel.
    s = _finish_seed(finish_id)
    gate = f32(0.30) + f32(0.70) * np.clip(L * f32(1.25), f32(0.0), f32(1.0)) * (f32(1.0) - dark)

    nt = _msc(h, w, [2, 4, 8], s ^ 0xA1) - f32(0.5)
    nt *= f32(120.0)
    nt *= gate
    M += nt
    nt = _msc(h, w, [5, 11, 21], s ^ 0xB2) - f32(0.5)
    nt *= f32(125.0)
    nt *= gate
    R += nt
    nt = _msc(h, w, [9, 19, 40], s ^ 0xC3) - f32(0.5)
    nt *= f32(120.0)
    nt *= gate
    CC += nt

    # 3) gold outline = hottest flash (lowest roughness, highest metal)
    ol = edge * np.clip(gold + white * f32(0.5), f32(0.0), f32(1.0))
    M += ol * f32(55.0)
    R -= ol * f32(70.0)

    np.clip(M, f32(0.0), f32(255.0), out=M)
    np.clip(R, f32(15.0), f32(255.0), out=R)
    np.clip(CC, f32(16.0), f32(255.0), out=CC)

    out = np.empty((h, w, 4), dtype=np.float32)
    if np.isscalar(m) or getattr(m, "ndim", 2) == 0 or float(np.min(m)) >= 1.0:
        # full-coverage mask (the common case): the outside term is zero, so the
        # per-channel composite collapses to the clipped channel itself.
        out[:, :, 0] = np.clip(M * f32(sm), f32(0.0), f32(255.0))
        out[:, :, 1] = R
        out[:, :, 2] = CC
    else:
        mf = m.astype(np.float32) if m.dtype != np.float32 else m
        outside = f32(1.0) - mf
        out[:, :, 0] = np.clip(M * f32(sm) * mf + f32(4.0) * outside, f32(0.0), f32(255.0))
        out[:, :, 1] = np.clip(R * mf + f32(120.0) * outside, f32(15.0), f32(255.0))
        out[:, :, 2] = np.clip(CC * mf + f32(80.0) * outside, f32(16.0), f32(255.0))
    out[:, :, 3] = 255
    return out.astype(np.uint8)


def _paint_from_asset(finish_id, paint, shape, mask, pm):
    # PERF 2026-06-13: identical blend (paint*(1-a) + tex*a, a = mask*strength),
    # re-expressed in float32 to avoid float64 promotion of the full-canvas
    # intermediates and to fold the per-channel (h,w,1)->(h,w,3) broadcast into a
    # single shared 2D weight. Bit-identical paint output (verified array_equal).
    f32 = np.float32
    h, w = _shape2(shape)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    tex = apply_zone_placement_rgb(tex, (h, w), mask=mask)
    strength = f32(np.clip(float(pm) * 0.98, 0.0, 1.0))
    a = (_mask2(mask, (h, w)) * strength)[:, :, None]      # (h,w,1) float32 weight
    inv = f32(1.0) - a
    p3 = paint[:, :, :3]
    np.multiply(p3, inv, out=p3)
    p3 += tex[:, :, :3] * a
    np.clip(paint, f32(0.0), f32(1.0), out=paint)
    return paint.astype(np.float32, copy=False)


def _spec_from_asset(finish_id, shape, mask, sm):
    h, w = _shape2(shape)
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    tex = apply_zone_placement_rgb(tex, (h, w), mask=mask)
    m = _mask2(mask, (h, w))
    return _dragon_spec_trace(tex, m, finish_id, sm)


def _make_paint_fn(finish_id):
    def paint_fn(paint, shape, mask, seed, pm, bb):
        return _paint_from_asset(finish_id, paint, shape, mask, pm)

    paint_fn.__name__ = f"paint_{finish_id}"
    return paint_fn




# ── 2026-08-31 spec rebuild ────────────────────────────────────────────────
# Owner: "keep the designs in place that's there now for the base paint and
# rework ALL of the specs." The authored spec PNG is no longer read; the spec is
# authored live from this finish's own painted plate by
# engine/paint_v2/cultural_spec_2026, which finds six material roles in the
# artwork and deals a complete material card to each from the shared deck. The
# paint path above is untouched.
def _new_spec(finish_id, shape, mask, sm):
    from engine.paint_v2 import cultural_spec_2026 as _CS
    _CS.ensure('forbidden_dragon', tuple(_FINISH_IDS), _load_rgb)
    h, w = _shape2(shape)
    m = _mask2(mask, (h, w))
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    # not every cultural module imports the placement helper
    _place = globals().get('apply_zone_placement_rgb')
    if _place is not None:
        tex = _place(tex, (h, w), mask=mask)
    spec, _story = _CS.build('forbidden_dragon', finish_id, tex, 51, float(sm))
    out = np.asarray(spec, np.float32)
    if out.shape[2] < 4:
        out = np.dstack([out, np.full((h, w, 1), 255.0, np.float32)])
    outside = 1.0 - m
    out[:, :, 0] = np.clip(out[:, :, 0] * m + 4.0 * outside, 0, 255)
    out[:, :, 1] = np.clip(out[:, :, 1] * m + 120.0 * outside, 15, 255)
    out[:, :, 2] = np.clip(out[:, :, 2] * m + 80.0 * outside, 16, 255)
    out[:, :, 3] = 255
    return out.astype(np.uint8)


def _make_spec_fn(finish_id):
    def spec_fn(shape, mask, seed, sm):
        return _new_spec(finish_id, shape, mask, sm)

    spec_fn.__name__ = f"spec_{finish_id}"
    return spec_fn


FORBIDDEN_DRAGON_MONOLITHICS = {
    finish_id: (_make_spec_fn(finish_id), _make_paint_fn(finish_id))
    for finish_id in _FINISH_IDS
}
