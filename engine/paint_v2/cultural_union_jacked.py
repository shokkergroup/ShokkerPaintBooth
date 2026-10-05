"""Cultural / Union Jacked — British mod & heritage image monolithics.

Paint plates live under ``assets/reference_textures/cultural/union_jacked/`` as
``{id}.png`` (footer cropped, 2048). Paired ``{id}_spec.png`` (baked scratch RGBA at
2048) is **loaded when present**, same pipeline as Viva Mexico: resize →
``_pre_adjust_viva_mexico_spec`` → mask / ``sm`` → ``_post_adjust_viva_mexico_spec``.
If ``*_spec.png`` is missing, M/R/Cc are built live from the paint plate via
``_scratch_spec_from_paint``.

Run ``python scripts/bake_union_jacked_specs.py`` after re-exporting paint textures.

**Chromatic-shift subset** (17 finishes, flag in ``manifest.json``): adds
**hue-phase modulation** on M and Cc — spatially varying metallic weight and
clearcoat lobes tied to paint hue. Base **albedo still comes only from the
paint plate**; this biases **per-pixel spec response**, which reads as **colour
travel / flip** under moving light next to saturated graphics (pearlescent /
thin-film style, without a second paint map).

Chromatic IDs: ``_CHROMATIC_SHIFT_IDS`` (loaded from ``manifest.json``).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from engine.paint_v2.cultural_viva_mexico import (
    _finish_rng_seed,
    _post_adjust_viva_mexico_spec,
    _pre_adjust_viva_mexico_spec,
    _viva_mexico_highlight_crest,
    _viva_mexico_paint_luma_edge,
)

_ROOT = Path(__file__).resolve().parents[2]
_ASSET_DIR = _ROOT / "assets" / "reference_textures" / "cultural" / "union_jacked"
_JPG_ASSET_DIR = _ASSET_DIR / "jpg_2048"


def _prefer_jpg_runtime() -> bool:
    value = os.environ.get("SPB_UNION_JACKED_USE_JPG", os.environ.get("SPB_CULTURAL_USE_JPG", "1"))
    return value.lower() not in {"0", "false", "no"}


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

_CHROMATIC_SHIFT_IDS = frozenset(
    fid for fid, meta in _FINISH_META.items() if meta.get("chromatic_shift")
)
_BOUNDED_SPEC_IDS = set(_FINISH_IDS)


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


@lru_cache(maxsize=128)
def _load_rgb_cached(finish_id, mtime_ns):
    path = _texture_path(finish_id)
    if not path.exists():
        raise FileNotFoundError(f"Missing Union Jacked texture: {path}")
    img = Image.open(path).convert("RGB")
    return (np.asarray(img, dtype=np.float32) / 255.0).astype(np.float32)


def _load_rgb(finish_id):
    path = _texture_path(finish_id)
    return _load_rgb_cached(finish_id, path.stat().st_mtime_ns)


@lru_cache(maxsize=128)
def _load_spec_cached(finish_id, mtime_ns):
    path = _spec_texture_path(finish_id)
    if not path.exists():
        raise FileNotFoundError(f"Missing Union Jacked spec map: {path}")
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def _load_spec(finish_id):
    path = _spec_texture_path(finish_id)
    return _load_spec_cached(finish_id, path.stat().st_mtime_ns)


def bake_union_jacked_scratch_spec_u8(finish_id: str) -> np.ndarray:
    """Deterministic RGBA uint8 scratch spec from ``{id}.png`` (for bake script)."""
    tex = _load_rgb(finish_id)
    h, w = tex.shape[:2]
    m = np.ones((h, w), dtype=np.float32)
    chrom = finish_id in _CHROMATIC_SHIFT_IDS
    spec = _scratch_spec_from_paint(tex, m, finish_id, chromatic_shift=chrom)
    return np.clip(spec, 0.0, 255.0).astype(np.uint8)


def _hue_radians(tex_rgb_hwc: np.ndarray) -> np.ndarray:
    """Hue in radians from linear RGB, shape (H,W)."""
    r = tex_rgb_hwc[:, :, 0]
    g = tex_rgb_hwc[:, :, 1]
    b = tex_rgb_hwc[:, :, 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    d = mx - mn + 1e-6
    h = np.zeros_like(mx)
    mask_r = mx == r
    h = np.where(mask_r & (g >= b), (g - b) / d, h)
    h = np.where(mask_r & (g < b), 6.0 + (g - b) / d, h)
    h = np.where(mx == g, (b - r) / d + 2.0, h)
    h = np.where(mx == b, (r - g) / d + 4.0, h)
    h = (h / 6.0) % 1.0
    return (h * (2.0 * np.pi)).astype(np.float32)


def _scratch_spec_from_paint(
    tex_rgb_hwc: np.ndarray,
    mask_hw: np.ndarray,
    finish_id: str,
    chromatic_shift: bool,
) -> np.ndarray:
    """Build float RGBA spec (0–255 scale in channels 0–2) from paint only."""
    m = np.clip(mask_hw.astype(np.float32), 0.0, 1.0)
    h, w = tex_rgb_hwc.shape[:2]
    gray, edge_n = _viva_mexico_paint_luma_edge(tex_rgb_hwc, mask_hw)
    streak_soft, _, _ = _viva_mexico_highlight_crest(tex_rgb_hwc, mask_hw)

    r = tex_rgb_hwc[:, :, 0]
    gch = tex_rgb_hwc[:, :, 1]
    b = tex_rgb_hwc[:, :, 2]
    mx = np.maximum(np.maximum(r, gch), b)
    mn = np.minimum(np.minimum(r, gch), b)
    sat = np.clip((mx - mn) / (mx + 1e-6), 0.0, 1.0)

    dark = gray < (34.0 / 255.0)
    dark_flat = dark & (edge_n < 0.22)

    # “Chrome / enamel” read: saturated or very bright, edged.
    chrome_w = np.clip(sat * 1.15, 0.0, 1.0) * (0.55 + 0.45 * np.clip(gray * 2.2, 0.0, 1.0))
    chrome_w = chrome_w * (1.0 - dark_flat.astype(np.float32) * 0.75)
    chrome_w = np.clip(chrome_w + edge_n * 0.38 * (1.0 - dark.astype(np.float32)), 0.0, 1.0)

    # Base metallic: push highs on graphics, sink matte voids.
    M = (
        18.0
        + chrome_w * 175.0
        + edge_n * 95.0 * (1.0 - dark_flat.astype(np.float32))
        + gray * 55.0 * sat
        + streak_soft * 115.0
    )
    # Higher floor than VM plates' authored voids — navy poster fields hit ``dark_flat`` often;
    # a low floor collides with DNA post-clamp and reads as an empty metallic (R) channel in UI.
    M = np.where(dark_flat, M * 0.58 + 46.0, M)

    # Roughness: glossy where chrome_w high; rough on fabric-like darks.
    R = (
        228.0
        - chrome_w * 118.0
        - edge_n * 62.0 * (1.0 - dark.astype(np.float32) * 0.5)
        - streak_soft * 88.0
        - sat * 35.0 * (1.0 - dark.astype(np.float32))
    )
    R = np.where(dark_flat, np.maximum(R, 198.0), R)

    # Clearcoat: DNA void in flat black; wet peaks on crests and brights.
    Cc = (
        10.0
        + (1.0 - dark_flat.astype(np.float32)) * (6.0 + chrome_w * 52.0)
        + edge_n * 38.0 * (1.0 - dark.astype(np.float32))
        + streak_soft * 62.0
        + np.clip(gray - 0.35, 0.0, 0.65) * 85.0
    )
    Cc = np.where(dark_flat, np.minimum(Cc, 14.0), Cc)
    peak_gloss = (streak_soft > 0.18) | (chrome_w > 0.72)
    Cc = np.where(peak_gloss & (~dark_flat), np.maximum(Cc, 16.0), Cc)

    # Seeded micro-flake / grit (distinct per finish).
    seed = _finish_rng_seed(finish_id)
    rng = np.random.default_rng(seed ^ 0xC0FFEE)
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    ys = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)

    gw = max(4, h // 9)
    gh = max(4, w // 9)
    grid = rng.random((gw, gh), dtype=np.float32)
    flake = cv2.resize((grid > 0.971).astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
    mid = np.clip((gray - 0.14) / 0.62, 0.0, 1.0) * np.clip((0.78 - gray) / 0.5, 0.0, 1.0)
    fl_w = flake * mid * m * (0.4 + 0.6 * edge_n) * (1.0 - dark_flat.astype(np.float32) * 0.9)
    M = np.clip(M + fl_w * 108.0, 0.0, 255.0)
    R = np.clip(R - fl_w * 72.0, 15.0, 255.0)
    Cc = np.where(fl_w > 0.35, Cc * 0.4 + 16.0 * 0.6, Cc)

    # Diagonal interference — breaks axis lock, reads “custom blend”.
    ph = float(seed % 997) * (np.pi / 512.0)
    interf = np.sin((xs + ys) * (180.0 + ph * 40)) * np.cos((xs * 1.07 - ys) * (220.0 - ph * 30))
    live = np.clip((gray - 0.10) / 0.75, 0.0, 1.0) * m * (1.0 - dark_flat.astype(np.float32) * 0.85)
    M = np.clip(M + np.abs(interf) * 22.0 * live, 0.0, 255.0)
    R = np.clip(R + interf * 16.0 * live, 15.0, 255.0)
    Cc = np.clip(Cc + interf * 12.0 * live * (0.5 + 0.5 * sat), 0.0, 255.0)

    # --- Micro-relief / height read (spec-only “3D pop”) ---
    gray_u8 = np.clip(gray * 255.0, 0.0, 255.0).astype(np.uint8)
    lap = cv2.Laplacian(gray_u8, cv2.CV_32F, ksize=3)
    lap_mag = np.abs(lap).astype(np.float32)
    lap_den = float(np.percentile(lap_mag, 99.5)) + 1e-3
    lap_n = np.clip(lap_mag / lap_den, 0.0, 1.0)
    lap_n = cv2.GaussianBlur(lap_n, (0, 0), 1.2)

    blur_big = cv2.GaussianBlur(gray_u8.astype(np.float32), (0, 0), 10.0)
    detail_hp = (gray * 255.0 - blur_big) / 120.0
    detail_w = np.clip(np.abs(detail_hp), 0.0, 1.0) * m * (1.0 - dark_flat.astype(np.float32))

    relief = np.clip(0.5 * lap_n + 0.5 * detail_w, 0.0, 1.0)
    rv = np.clip((gray - 0.07) / 0.85, 0.0, 1.0)
    ridge = relief * m * rv * (0.45 + 0.55 * sat) * (1.0 - dark_flat.astype(np.float32) * 0.75)
    ridge = np.clip(ridge * (0.55 + 0.45 * np.clip(edge_n * 1.4, 0.0, 1.0)), 0.0, 1.0)

    M = np.clip(M + ridge * 118.0, 0.0, 255.0)
    R = np.clip(R - ridge * 62.0, 15.0, 255.0)
    Cc = np.clip(Cc + ridge * 78.0 * (0.35 + 0.65 * chrome_w), 0.0, 255.0)

    # --- Chromatic-shift layer: hue-modulated M + Cc (view/light travel) ---
    if chromatic_shift:
        hue = _hue_radians(tex_rgb_hwc)
        # Spatial carrier + hue phase → different regions get different spec bias.
        carrier = np.sin(hue * 2.1 + xs * 38.0 + ys * 27.0 + ph) * np.cos(
            hue * 1.4 - xs * 22.0 + ys * 41.0
        )
        carrier2 = np.sin(hue * 2.7 + xs * 61.0 - ys * 48.0 + ph * 1.3) * np.cos(
            hue * 1.9 + xs * 19.0 + ys * 55.0
        )
        chrom_w = sat * (0.35 + 0.65 * edge_n) * m * (1.0 - dark_flat.astype(np.float32) * 0.95)
        # Stronger M / Cc and second harmonic so packed RGB (M/Rough/Cc) shows chroma
        # in the channel preview, not only mid-high green (roughness).
        M = np.clip(M + carrier * 88.0 * chrom_w + carrier2 * 38.0 * chrom_w, 0.0, 255.0)
        R = np.clip(
            R - np.abs(carrier) * 32.0 * chrom_w - np.abs(carrier2) * 18.0 * chrom_w,
            15.0,
            255.0,
        )
        # Hue-tinted roughness wobble — visible as non-green variation in the G channel preview.
        R = np.clip(R + np.sin(hue * 2.4 + ys * 72.0) * 22.0 * chrom_w, 15.0, 255.0)
        # Cc lobes: pearl / gloss swing (stay mostly above void, below extreme candy).
        Cc = np.clip(
            Cc
            + carrier * 48.0 * chrom_w
            + carrier2 * 24.0 * chrom_w
            + np.sin(hue * 3.0) * 26.0 * sat * m
            + np.cos(hue * 1.15 + xs * 44.0) * 20.0 * chrom_w,
            0.0,
            120.0,
        )

    M = np.clip(M, 0.0, 255.0)
    R = np.clip(R, 15.0, 255.0)
    Cc = np.clip(Cc, 0.0, 255.0)

    out = np.zeros((h, w, 4), dtype=np.float32)
    out[:, :, 0] = M
    out[:, :, 1] = R
    out[:, :, 2] = Cc
    out[:, :, 3] = 255.0
    return out


def _paint_from_asset(finish_id, paint, shape, mask, pm):
    h, w = _shape2(shape)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    m3 = _mask2(mask, (h, w))[:, :, None]
    # SPB union_jacked perf 2026-06-13: the prior blend promoted the whole
    # 2048x2048x3 expression to float64 (np.clip returns a float64 scalar and the
    # ``1.0`` literal is a Python float), allocated ~5 full temporaries, then cast
    # back to float32. Keep everything float32 and use the lerp identity
    #   a*(1-w) + b*w == a + (b-a)*w
    # writing back in place (1 temporary). Mathematically identical; only sub-ULP
    # float32-vs-float64 rounding differs (verified bit-stable after the final clip
    # and the downstream 8-bit quantization). Visually equivalent.
    strength = np.float32(np.clip(float(pm) * 0.98, 0.0, 1.0))
    weight = m3 * strength  # float32 (H,W,1)
    p3 = paint[:, :, :3]
    # p3 += (tex - p3) * weight, but tex is a cached read-only-ish array; build a
    # single delta temporary then fused-multiply-add in place.
    delta = tex[:, :, :3] - p3
    delta *= weight
    p3 += delta
    np.clip(p3, 0.0, 1.0, out=p3)
    return paint if paint.dtype == np.float32 else paint.astype(np.float32)


def _spec_from_asset(finish_id, shape, mask, sm):
    h, w = _shape2(shape)
    m = _mask2(mask, (h, w))
    if finish_id in _BOUNDED_SPEC_IDS and max(h, w) > 1024:
        # SPB paint-finish perf loop 2026-05-31; owner: "Speed is king in this app."
        # Slow Union Jacked rows measured 5.04-6.14s -> 1.67-2.04s. Keep authored paint full-res;
        # run the Viva-style spec polish on a bounded grid and restore final mask.
        scale = 1024.0 / float(max(h, w))
        sh = max(256, int(round(h * scale)))
        sw = max(256, int(round(w * scale)))
        m_small = cv2.resize(m, (sw, sh), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        outside_small = 1.0 - m_small
        tex = _resize(_load_rgb(finish_id), (sh, sw), cv2.INTER_AREA)
        spec_path = _spec_texture_path(finish_id)
        if spec_path.exists():
            spec = _resize(_load_spec(finish_id), (sh, sw), cv2.INTER_AREA).astype(np.float32)
        else:
            chrom = finish_id in _CHROMATIC_SHIFT_IDS
            spec = _scratch_spec_from_paint(tex, m_small, finish_id, chromatic_shift=chrom)
        _pre_adjust_viva_mexico_spec(
            spec, tex, m_small, finish_id, dark_interior_flatten=0.38
        )
        spec[:, :, 0] = np.clip(spec[:, :, 0] * sm * m_small + 4.0 * outside_small, 0, 255)
        spec[:, :, 1] = np.clip(spec[:, :, 1] * m_small + 120.0 * outside_small, 15, 255)
        spec[:, :, 2] = np.clip(spec[:, :, 2] * m_small + 80.0 * outside_small, 16, 255)
        spec[:, :, 3] = 255
        # SPB union_jacked perf 2026-06-13: _post_adjust returns uint8; cv2.resize
        # of a float32 array already yields float32, so the trailing .astype(float32)
        # on the resize was a redundant full 2048^2x4 copy. Cast once before resize.
        out = _post_adjust_viva_mexico_spec(
            spec.astype(np.uint8),
            tex,
            m_small,
            void_metallic_max=92.0,
            void_roughness_min=158.0,
            void_clearcoat_max=44.0,
        ).astype(np.float32)
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
        outside = 1.0 - m
        out[:, :, 0] = np.clip(out[:, :, 0] * m + 4.0 * outside, 0, 255)
        out[:, :, 1] = np.clip(out[:, :, 1] * m + 120.0 * outside, 15, 255)
        out[:, :, 2] = np.clip(out[:, :, 2] * m + 80.0 * outside, 16, 255)
        out[:, :, 3] = 255
        return out.astype(np.uint8)

    outside = 1.0 - m
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    spec_path = _spec_texture_path(finish_id)
    if spec_path.exists():
        spec = _resize(_load_spec(finish_id), (h, w), cv2.INTER_AREA).astype(np.float32)
    else:
        chrom = finish_id in _CHROMATIC_SHIFT_IDS
        spec = _scratch_spec_from_paint(tex, m, finish_id, chromatic_shift=chrom)
    # Softer dark-interior flatten than VM defaults — Union Jacked paint is mostly deep ink with
    # silver line art; stock DNA treats that as ``void`` and zeros metallic (preview “R” / M channel).
    _pre_adjust_viva_mexico_spec(
        spec, tex, m, finish_id, dark_interior_flatten=0.38
    )

    spec[:, :, 0] = np.clip(spec[:, :, 0] * sm * m + 4.0 * outside, 0, 255)
    spec[:, :, 1] = np.clip(spec[:, :, 1] * m + 120.0 * outside, 15, 255)
    spec[:, :, 2] = np.clip(spec[:, :, 2] * m + 80.0 * outside, 16, 255)
    spec[:, :, 3] = 255
    out = spec.astype(np.uint8)
    out = _post_adjust_viva_mexico_spec(
        out,
        tex,
        m,
        void_metallic_max=92.0,
        void_roughness_min=158.0,
        void_clearcoat_max=44.0,
    )
    return out


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
    _CS.ensure('union_jacked', tuple(_FINISH_IDS), _load_rgb)
    h, w = _shape2(shape)
    m = _mask2(mask, (h, w))
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    # not every cultural module imports the placement helper
    _place = globals().get('apply_zone_placement_rgb')
    if _place is not None:
        tex = _place(tex, (h, w), mask=mask)
    spec, _story = _CS.build('union_jacked', finish_id, tex, 51, float(sm))
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


UNION_JACKED_MONOLITHICS = (
    {finish_id: (_make_spec_fn(finish_id), _make_paint_fn(finish_id)) for finish_id in _FINISH_IDS}
    if _FINISH_IDS
    else {}
)
