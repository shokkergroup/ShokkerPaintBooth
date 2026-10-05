"""Ricky reference-art spec overlays, batch 2.

SPB-RATE10 2026-05-27 reference batch 2.
Owner verdict snippet: "10 more Dangerous Animals and 10 more Voodoo inspired
finishes... cutting off the names and numbers at the bottom and properly
sizing them for the 2048x2048 canvas size. SPEC OVERLAYS of course".
Metric movement is recorded in the baked asset manifest and RATE10 thumbnail
verification pass for these twenty reference-backed overlays.
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
_ASSET_DIR = Path(_rrd("spec_overlays/ricky_reference_batch2"))
_RESIZE_CACHE: "OrderedDict[tuple, np.ndarray]" = OrderedDict()
_CACHE_MAX = 48


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


def _refresh_manifest() -> None:
    global _MANIFEST, _META
    _MANIFEST = _load_manifest()
    _META = {str(item["id"]): item for item in _MANIFEST.get("finishes", []) if item.get("id")}


def _cache_put(key: tuple, value: np.ndarray) -> np.ndarray:
    _RESIZE_CACHE[key] = value
    _RESIZE_CACHE.move_to_end(key)
    while len(_RESIZE_CACHE) > _CACHE_MAX:
        _RESIZE_CACHE.popitem(last=False)
    return value


@lru_cache(maxsize=48)
def _load_spec_cached(finish_id: str, mtime_ns: int) -> np.ndarray:
    del mtime_ns
    meta = _META.get(finish_id)
    if not meta:
        _refresh_manifest()
        meta = _META.get(finish_id)
    if not meta:
        raise KeyError(f"Unknown Ricky batch2 reference spec overlay: {finish_id}")
    path = _ASSET_DIR / str(meta["spec"])
    if not path.exists():
        raise FileNotFoundError(f"Missing Ricky batch2 reference spec: {path}")
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
        _refresh_manifest()
        meta = _META.get(finish_id)
    if not meta:
        raise KeyError(f"Unknown Ricky batch2 reference spec overlay: {finish_id}")
    path = _ASSET_DIR / str(meta["spec"])
    key = (finish_id, path.stat().st_mtime_ns, int(h), int(w))
    cached = _RESIZE_CACHE.get(key)
    if cached is not None:
        _RESIZE_CACHE.move_to_end(key)
        # No .copy() needed: arr is only READ below (every clip/abs/mul
        # allocates a fresh array; arr is never mutated in place), so we can
        # use the cached buffer directly. Saves a full 2048^2x3 copy/call.
        arr = cached
    else:
        src = _load_spec(finish_id)
        if src.shape[:2] == (h, w):
            arr = src.copy()
        else:
            arr = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)
        # _cache_put returns the stored array; no extra copy — see note above.
        arr = _cache_put(key, arr)

    # Keep the reference art authoritative while adding small lighting-life
    # shifts so repeated zones do not look like a frozen bitmap under spec.
    # NOTE: this block is a hot path (runs on EVERY spec render at 2048^2).
    # It is hand-fused to be BIT-IDENTICAL to the original arithmetic while
    # avoiding temporaries: in-place sin/cos via out=, fused float32 scales,
    # and direct writes into a preallocated (h,w,3) buffer instead of
    # np.stack (verified np.array_equal across sm/seed in _NIGHTLY perf_fix).
    phase = float((int(seed) + len(finish_id) * 113) % 8192) * (np.pi / 4096.0)
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    ys = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)

    # shimmer = sin(xs*(91+phase) + ys*(43-phase*0.31))
    shimmer = xs * np.float32(91.0 + phase) + ys * np.float32(43.0 - phase * 0.31)
    np.sin(shimmer, out=shimmer)
    # filament = cos(xs*(233-phase*0.43) - ys*(181+phase*0.22))
    filament = xs * np.float32(233.0 - phase * 0.43) - ys * np.float32(181.0 + phase * 0.22)
    np.cos(filament, out=filament)

    # live = shimmer*0.010 + filament*0.006  (float32)
    live = shimmer
    live *= np.float32(0.010)
    filament *= np.float32(0.006)
    live += filament
    del filament

    out = np.empty((h, w, 3), dtype=np.float32)
    # M = clip(arr0 + abs(live)*0.040, 0, 1)
    m = np.abs(live)
    m *= np.float32(0.040)
    m += arr[:, :, 0]
    np.clip(m, 0.0, 1.0, out=out[:, :, 0])
    # R = clip(arr1 + live*0.030, 0.06, 0.98)
    r = live * np.float32(0.030)
    r += arr[:, :, 1]
    np.clip(r, 0.06, 0.98, out=out[:, :, 1])
    # CC = clip(arr2 - live*0.028, 0, 1)
    live *= np.float32(0.028)
    cc = arr[:, :, 2] - live
    np.clip(cc, 0.0, 1.0, out=out[:, :, 2])
    return _validate_spec_output(_sm_scale(out, sm), finish_id)


def ricky_king_cobra_coil(shape, seed, sm, **kwargs):
    return _reference_spec("king_cobra_coil", shape, seed, sm, **kwargs)


def ricky_widow_web_venom(shape, seed, sm, **kwargs):
    return _reference_spec("widow_web_venom", shape, seed, sm, **kwargs)


def ricky_tiger_fang_fracture(shape, seed, sm, **kwargs):
    return _reference_spec("tiger_fang_fracture", shape, seed, sm, **kwargs)


def ricky_scorpion_ember_hex(shape, seed, sm, **kwargs):
    return _reference_spec("scorpion_ember_hex", shape, seed, sm, **kwargs)


def ricky_hornet_swarm_static(shape, seed, sm, **kwargs):
    return _reference_spec("hornet_swarm_static", shape, seed, sm, **kwargs)


def ricky_croc_delta_armor(shape, seed, sm, **kwargs):
    return _reference_spec("croc_delta_armor", shape, seed, sm, **kwargs)


def ricky_panther_shadow_claw(shape, seed, sm, **kwargs):
    return _reference_spec("panther_shadow_claw", shape, seed, sm, **kwargs)


def ricky_piranha_frenzy_current(shape, seed, sm, **kwargs):
    return _reference_spec("piranha_frenzy_current", shape, seed, sm, **kwargs)


def ricky_jellyshock_drift(shape, seed, sm, **kwargs):
    return _reference_spec("jellyshock_drift", shape, seed, sm, **kwargs)


def ricky_sharkbite_riptide(shape, seed, sm, **kwargs):
    return _reference_spec("sharkbite_riptide", shape, seed, sm, **kwargs)


def ricky_bayou_hex_burlap(shape, seed, sm, **kwargs):
    return _reference_spec("bayou_hex_burlap", shape, seed, sm, **kwargs)


def ricky_candle_wax_veve(shape, seed, sm, **kwargs):
    return _reference_spec("candle_wax_veve", shape, seed, sm, **kwargs)


def ricky_pins_and_thread(shape, seed, sm, **kwargs):
    return _reference_spec("pins_and_thread", shape, seed, sm, **kwargs)


def ricky_swamp_charm_patina(shape, seed, sm, **kwargs):
    return _reference_spec("swamp_charm_patina", shape, seed, sm, **kwargs)


def ricky_mojo_bag_grain(shape, seed, sm, **kwargs):
    return _reference_spec("mojo_bag_grain", shape, seed, sm, **kwargs)


def ricky_midnight_gris_gris(shape, seed, sm, **kwargs):
    return _reference_spec("midnight_gris_gris", shape, seed, sm, **kwargs)


def ricky_bayou_smoke_script(shape, seed, sm, **kwargs):
    return _reference_spec("bayou_smoke_script", shape, seed, sm, **kwargs)


def ricky_coffin_nail_rust(shape, seed, sm, **kwargs):
    return _reference_spec("coffin_nail_rust", shape, seed, sm, **kwargs)


def ricky_root_doctor_copper(shape, seed, sm, **kwargs):
    return _reference_spec("root_doctor_copper", shape, seed, sm, **kwargs)


def ricky_spanish_moss_static(shape, seed, sm, **kwargs):
    return _reference_spec("spanish_moss_static", shape, seed, sm, **kwargs)


def ricky_seigaiha_chrome(shape, seed, sm, **kwargs):
    return _reference_spec("seigaiha_chrome", shape, seed, sm, **kwargs)


def ricky_sakura_static(shape, seed, sm, **kwargs):
    return _reference_spec("sakura_static", shape, seed, sm, **kwargs)


def ricky_kintsugi_rift(shape, seed, sm, **kwargs):
    return _reference_spec("kintsugi_rift", shape, seed, sm, **kwargs)


def ricky_torii_ember_lattice(shape, seed, sm, **kwargs):
    return _reference_spec("torii_ember_lattice", shape, seed, sm, **kwargs)


def ricky_oni_veil_mosaic(shape, seed, sm, **kwargs):
    return _reference_spec("oni_veil_mosaic", shape, seed, sm, **kwargs)


def ricky_shogun_scale_brocade(shape, seed, sm, **kwargs):
    return _reference_spec("shogun_scale_brocade", shape, seed, sm, **kwargs)


def ricky_kyoto_lantern_filigree(shape, seed, sm, **kwargs):
    return _reference_spec("kyoto_lantern_filigree", shape, seed, sm, **kwargs)


def ricky_bonsai_drift_circuit(shape, seed, sm, **kwargs):
    return _reference_spec("bonsai_drift_circuit", shape, seed, sm, **kwargs)


def ricky_fuji_frost_crest(shape, seed, sm, **kwargs):
    return _reference_spec("fuji_frost_crest", shape, seed, sm, **kwargs)


def ricky_rising_sun_prismwave(shape, seed, sm, **kwargs):
    return _reference_spec("rising_sun_prismwave", shape, seed, sm, **kwargs)


for _fn in (
    ricky_king_cobra_coil,
    ricky_widow_web_venom,
    ricky_tiger_fang_fracture,
    ricky_scorpion_ember_hex,
    ricky_hornet_swarm_static,
    ricky_croc_delta_armor,
    ricky_panther_shadow_claw,
    ricky_piranha_frenzy_current,
    ricky_jellyshock_drift,
    ricky_sharkbite_riptide,
    ricky_bayou_hex_burlap,
    ricky_candle_wax_veve,
    ricky_pins_and_thread,
    ricky_swamp_charm_patina,
    ricky_mojo_bag_grain,
    ricky_midnight_gris_gris,
    ricky_bayou_smoke_script,
    ricky_coffin_nail_rust,
    ricky_root_doctor_copper,
    ricky_spanish_moss_static,
    ricky_seigaiha_chrome,
    ricky_sakura_static,
    ricky_kintsugi_rift,
    ricky_torii_ember_lattice,
    ricky_oni_veil_mosaic,
    ricky_shogun_scale_brocade,
    ricky_kyoto_lantern_filigree,
    ricky_bonsai_drift_circuit,
    ricky_fuji_frost_crest,
    ricky_rising_sun_prismwave,
):
    _fn._spb_concept_complete = True
