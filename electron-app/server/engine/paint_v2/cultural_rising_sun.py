"""Cultural / Rising Sun image-based monolithic finishes.

The Rising Sun set uses prepared 2048 paint plates plus paired M/R/CC spec
plates. Keeping the artwork in assets lets the finish stay faithful to the
reference cards while still behaving like a married paint/spec material.

**Spec pipeline (all manifest IDs):** the same catalog-wide procedural pass as
Viva Mexico — paint-driven luma/edge, chromatic M/R/Cc triplets, ridge relief,
sparse accents, crest protection, multi-octave / nano detail, DNA void clamp —
see `cultural_viva_mexico.py` and `VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md`.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from engine.paint_v2.cultural_viva_mexico import (
    _post_adjust_viva_mexico_spec,
    _pre_adjust_viva_mexico_spec,
)


_ROOT = Path(__file__).resolve().parents[2]
_ASSET_DIR = _ROOT / "assets" / "reference_textures" / "cultural" / "rising_sun"
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

_FALLBACK_FINISH_IDS = (
    "rs_rising_sun_flare",
    "rs_oni_bloodshift",
    "rs_sakura_storm",
    "rs_hakuryu_ice",
    "rs_kuro_dragon",
    "rs_bamboo_zen",
    "rs_temple_gold",
    "rs_geisha_whisper",
    "rs_thunder_dragon",
    "rs_koi_ascension",
    "rs_kyoto_lantern",
    "rs_shibuya_pulse",
    "rs_kintsugi_moon",
    "rs_fuji_dawn",
    "rs_matcha_ceremony",
    "rs_kabuki_inferno",
    "rs_indigo_tsunami",
    "rs_vermilion_torii",
    "rs_crane_garden",
    "rs_sumi_eclipse",
    "rs_yurei_veil",
    "rs_kitsune_ember",
    "rs_oni_nocturne",
    "rs_gashadokuro_moon",
    "rs_jorogumo_silk",
    "rs_tengu_storm",
    "rs_bakeneko_velvet",
    "rs_nure_onna_tide",
    "rs_hyakki_parade",
    "rs_bell_of_damned",
    "rs_sakura_cascade",
    "rs_wisteria_reverie",
    "rs_lotus_reverie",
    "rs_peony_festival",
    "rs_iris_rain",
    "rs_camellia_glow",
    "rs_plum_blossom_dawn",
    "rs_chrysanthemum_sun",
    "rs_hydrangea_mist",
    "rs_koi_pond_bloom",
    "rs_bosozoku_riot",
    "rs_wangan_midnight_pulse",
    "rs_touge_apex",
    "rs_drift_hanami_oversteer",
    "rs_kaido_chrome_bloom",
    "rs_dekotora_electric_freight",
    "rs_time_attack_grid_shock",
)


def _manifest_finish_ids():
    path = _ASSET_DIR / "manifest.json"
    if not path.exists():
        return _FALLBACK_FINISH_IDS
    try:
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        ids = tuple(item["id"] for item in data.get("finishes", []) if item.get("id"))
        return ids or _FALLBACK_FINISH_IDS
    except Exception:
        return _FALLBACK_FINISH_IDS


_FINISH_IDS = _manifest_finish_ids()
_PAINT_FINE_DETAIL_IDS = {"rs_gashadokuro_moon", "rs_kinpaku_blaze"}
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


def _normalize(a):
    a = np.asarray(a, dtype=np.float32)
    lo = float(np.percentile(a, 1.0))
    hi = float(np.percentile(a, 99.0))
    if hi <= lo:
        return np.zeros_like(a, dtype=np.float32)
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def _ridge(axis, scale, phase, sharp):
    return np.clip(1.0 - np.abs(np.sin((axis * scale + phase) * np.pi)) * sharp, 0.0, 1.0).astype(np.float32)


def _micro_fleck(shape, seed, cell, threshold):
    h, w = _shape2(shape)
    cell = max(2, int(cell))
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, h // cell), max(2, w // cell)), dtype=np.float32)
    fleck = (small > float(threshold)).astype(np.float32)
    shade = rng.random(small.shape, dtype=np.float32) * fleck
    fleck = cv2.resize(fleck * (0.45 + shade * 0.55), (w, h), interpolation=cv2.INTER_NEAREST)
    return _normalize(fleck)


def _paint_micro_detail(finish_id, tex):
    if finish_id not in _PAINT_FINE_DETAIL_IDS:
        return tex
    h, w = tex.shape[:2]
    if max(h, w) > 1024:
        # SPB paint-finish perf loop 2026-05-31; owner: "Speed is king in this app."
        # rs_kinpaku_blaze measured 6301.6ms -> 2428.9ms. Keep the 2048 authored plate intact,
        # but build the expensive fine-detail overlay as a bounded-grid delta.
        scale = 1024.0 / float(max(h, w))
        sh = max(256, int(round(h * scale)))
        sw = max(256, int(round(w * scale)))
        small = cv2.resize(tex, (sw, sh), interpolation=cv2.INTER_AREA).astype(np.float32)
        adjusted = _paint_micro_detail(finish_id, small)
        delta = cv2.resize(adjusted - small, (w, h), interpolation=cv2.INTER_LINEAR)
        return np.clip(tex + delta, 0.0, 1.0).astype(np.float32)
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    luma = np.clip(tex @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32), 0.0, 1.0)
    blur = cv2.GaussianBlur(luma, (0, 0), 1.2)
    high = _normalize(np.abs(luma - blur))
    edge = _normalize(np.abs(cv2.Laplacian(luma, cv2.CV_32F, ksize=3)))
    phase = 0.37 if finish_id == "rs_gashadokuro_moon" else 0.61

    if finish_id == "rs_gashadokuro_moon":
        rng = np.random.default_rng(41189)
        bone_noise = rng.random((h, w), dtype=np.float32) - 0.5
        bone_dust = _micro_fleck((h, w), 41101, 2, 0.720)
        ash_pin = _micro_fleck((h, w), 41157, 3, 0.820)
        hairline = _ridge(x * 0.74 - y * 1.36 + high * 0.18, 184.0, phase, 58.0)
        rib_tick = _ridge(x * 1.42 + y * 0.58 + edge * 0.12, 154.0, phase * 1.7, 52.0)
        bright = np.clip(bone_dust * 0.40 + ash_pin * 0.34 + hairline * 0.28 + edge * 0.20, 0, 1)
        dark = np.clip(bone_dust * 0.18 + rib_tick * 0.30 + high * 0.12 + ash_pin * 0.10, 0, 1)
        tint = np.array([0.86, 0.88, 0.80], dtype=np.float32)
        tex = tex * (1.0 - dark[:, :, None] * 0.115) + tint * bright[:, :, None] * 0.135
        tex = tex + bone_noise[:, :, None] * np.array([0.158, 0.162, 0.146], dtype=np.float32)
    else:
        rng = np.random.default_rng(42203)
        foil_noise = rng.random((h, w), dtype=np.float32) - 0.5
        foil_grain = _micro_fleck((h, w), 42101, 2, 0.680)
        foil_crack = _ridge(x * 1.18 + y * 0.76 + np.sin(y * np.pi * 8.0) * 0.032 + high * 0.10, 206.0, phase, 60.0)
        copper_pin = _micro_fleck((h, w), 42157, 3, 0.780)
        leaf_tick = _ridge(x * -0.92 + y * 1.28 + edge * 0.10, 178.0, phase * 1.4, 54.0)
        bright = np.clip(foil_grain * 0.46 + foil_crack * 0.32 + copper_pin * 0.30 + edge * 0.18, 0, 1)
        dark = np.clip(foil_grain * 0.14 + foil_crack * 0.22 + leaf_tick * 0.20 + high * 0.10, 0, 1)
        warm = np.array([1.00, 0.72, 0.30], dtype=np.float32)
        copper = np.array([0.92, 0.33, 0.14], dtype=np.float32)
        tex = tex * (1.0 - dark[:, :, None] * 0.090) + warm * bright[:, :, None] * 0.125 + copper * copper_pin[:, :, None] * 0.070
        tex = tex + foil_noise[:, :, None] * np.array([0.145, 0.102, 0.055], dtype=np.float32)
    return np.clip(tex, 0.0, 1.0).astype(np.float32)


@lru_cache(maxsize=96)
def _load_rgb_cached(finish_id, mtime_ns):
    path = _texture_path(finish_id)
    if not path.exists():
        raise FileNotFoundError(f"Missing Rising Sun texture: {path}")
    img = Image.open(path).convert("RGB")
    return (np.asarray(img, dtype=np.float32) / 255.0).astype(np.float32)


def _load_rgb(finish_id):
    path = _texture_path(finish_id)
    return _load_rgb_cached(finish_id, path.stat().st_mtime_ns)


@lru_cache(maxsize=96)
def _load_spec_cached(finish_id, mtime_ns):
    path = _spec_texture_path(finish_id)
    if not path.exists():
        raise FileNotFoundError(f"Missing Rising Sun spec map: {path}")
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def _load_spec(finish_id):
    path = _spec_texture_path(finish_id)
    return _load_spec_cached(finish_id, path.stat().st_mtime_ns)


def _paint_from_asset(finish_id, paint, shape, mask, pm):
    h, w = _shape2(shape)
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    tex = _paint_micro_detail(finish_id, _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA))
    m3 = _mask2(mask, (h, w))[:, :, None]
    strength = np.clip(float(pm) * 0.98, 0.0, 1.0)
    paint[:, :, :3] = paint[:, :, :3] * (1.0 - m3 * strength) + tex[:, :, :3] * (m3 * strength)
    return np.clip(paint, 0.0, 1.0).astype(np.float32)


def _post_adjust_rs_bell_of_damned_spec(spec, luma_hw, mask_hw):
    """DNA-driven remap for rs_bell_of_damned only.

    Report showed dark gloss leak + void floor weak + daylight sim flash dead.
    Hint targets on dark paint: M low, R high (matte), CC low; preserve sharper
    lacquer lanes where the plate reads brighter for pins / Full Sun rigs.
    """
    m = np.clip(mask_hw.astype(np.float32), 0.0, 1.0)
    M = spec[:, :, 0]
    R = spec[:, :, 1]
    Cc = spec[:, :, 2]

    dark_w = np.power(np.clip((0.38 - luma_hw) / 0.28, 0.0, 1.0), 1.12)
    blend = dark_w * 0.78 * m
    M[:] = np.clip(M * (1.0 - blend) + 10.0 * blend, 0.0, 255.0)
    R[:] = np.clip(R * (1.0 - blend) + 230.0 * blend, 15.0, 255.0)
    Cc[:] = np.clip(Cc * (1.0 - blend) + 13.0 * blend, 16.0, 255.0)

    bright = np.power(np.clip((luma_hw - 0.32) / 0.48, 0.0, 1.0), 1.9)
    hi_w = bright * (1.0 - dark_w * 0.72) * m
    M[:] = np.clip(M + hi_w * 32.0, 0.0, 255.0)
    R[:] = np.clip(R - hi_w * 48.0, 15.0, 255.0)
    Cc[:] = np.clip(Cc + hi_w * 40.0, 16.0, 255.0)

    sel = m > 0.5
    if np.any(sel):
        thr = float(np.percentile(luma_hw[sel], 7.0))
        deepest = sel & (luma_hw <= thr)
        if np.any(deepest):
            M[:] = np.where(deepest, np.minimum(M, 5.0), M)
            R[:] = np.where(deepest, np.maximum(R, 240.0), R)
            Cc[:] = np.where(deepest, np.minimum(Cc, 9.0), Cc)


def _spec_from_asset(finish_id, shape, mask, sm):
    h, w = _shape2(shape)
    m = _mask2(mask, (h, w))
    if finish_id in _BOUNDED_SPEC_IDS and max(h, w) > 1024:
        # Same perf loop as paint overlay: 6301.6ms -> 2428.9ms after bounded spec polish.
        # The heavy Viva-style polish is spec-only, so run it on a bounded grid and
        # restore exact final masking at the requested resolution.
        scale = 1024.0 / float(max(h, w))
        sh = max(256, int(round(h * scale)))
        sw = max(256, int(round(w * scale)))
        spec = _resize(_load_spec(finish_id), (sh, sw), cv2.INTER_AREA).astype(np.float32)
        tex = _resize(_load_rgb(finish_id), (sh, sw), cv2.INTER_AREA)
        m_small = cv2.resize(m, (sw, sh), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        outside_small = 1.0 - m_small

        _pre_adjust_viva_mexico_spec(spec, tex, m_small, finish_id)
        spec[:, :, 0] = np.clip(spec[:, :, 0] * sm * m_small + 4.0 * outside_small, 0, 255)
        spec[:, :, 1] = np.clip(spec[:, :, 1] * m_small + 120.0 * outside_small, 15, 255)
        spec[:, :, 2] = np.clip(spec[:, :, 2] * m_small + 80.0 * outside_small, 16, 255)
        spec[:, :, 3] = 255
        out = _post_adjust_viva_mexico_spec(spec.astype(np.uint8), tex, m_small).astype(np.float32)
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        outside = 1.0 - m
        out[:, :, 0] = np.clip(out[:, :, 0] * m + 4.0 * outside, 0, 255)
        out[:, :, 1] = np.clip(out[:, :, 1] * m + 120.0 * outside, 15, 255)
        out[:, :, 2] = np.clip(out[:, :, 2] * m + 80.0 * outside, 16, 255)
        out[:, :, 3] = 255
        return out.astype(np.uint8)

    spec = _resize(_load_spec(finish_id), (h, w), cv2.INTER_AREA).astype(np.float32)
    outside = 1.0 - m
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)

    # Finish-specific DNA hint (narrow); catalog-wide enhancement stacks on top.
    if finish_id == "rs_bell_of_damned":
        luma = np.clip(
            tex @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32),
            0.0,
            1.0,
        )
        _post_adjust_rs_bell_of_damned_spec(spec, luma, m)

    _pre_adjust_viva_mexico_spec(spec, tex, m, finish_id)

    spec[:, :, 0] = np.clip(spec[:, :, 0] * sm * m + 4.0 * outside, 0, 255)
    spec[:, :, 1] = np.clip(spec[:, :, 1] * m + 120.0 * outside, 15, 255)
    spec[:, :, 2] = np.clip(spec[:, :, 2] * m + 80.0 * outside, 16, 255)
    spec[:, :, 3] = 255
    out = spec.astype(np.uint8)
    out = _post_adjust_viva_mexico_spec(out, tex, m)
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
    _CS.ensure('rising_sun', tuple(_FINISH_IDS), _load_rgb)
    h, w = _shape2(shape)
    m = _mask2(mask, (h, w))
    tex = _resize(_load_rgb(finish_id), (h, w), cv2.INTER_AREA)
    # not every cultural module imports the placement helper
    _place = globals().get('apply_zone_placement_rgb')
    if _place is not None:
        tex = _place(tex, (h, w), mask=mask)
    spec, _story = _CS.build('rising_sun', finish_id, tex, 51, float(sm))
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


RISING_SUN_MONOLITHICS = {
    finish_id: (_make_spec_fn(finish_id), _make_paint_fn(finish_id))
    for finish_id in _FINISH_IDS
}

