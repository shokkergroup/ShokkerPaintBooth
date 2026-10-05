"""Live Neon Underground v4 registry adapters.

The v3 slate passed its numerical gate but failed owner contact: 25 variations
of one dark microtexture grammar, no tuner-nightlife silhouette, and none of
Oil Slick's broad continuous-field optical causality. V4 keeps the stable IDs
while replacing every builder with a distinct broad carrier, fixed-threshold
M/R/Cc response, fine attached anatomy, and an authored A/B optical witness.

SPB-105, tick NU-V4-LIVE-1 (2026-08-27). Owner verdict governs acceptance;
the metrics are diagnostics only.
"""
from __future__ import annotations

from collections import OrderedDict
from importlib import import_module
from threading import RLock

import cv2
import numpy as np

from .neon_underground_v4.catalog import CATALOG as V4_CATALOG, module_name as v4_module_name


GROUP = "★ NEON UNDERGROUND"

# id -> (builder module, builder name, display name, swatch, material-process copy)
# CATALOG owns both the deliberate live order and all user-facing identity.
NEON_FINISHES = {
    fid: (v4_module_name(fid), "build", name, swatch, desc)
    for fid, (_stem, name, swatch, desc) in V4_CATALOG.items()
}

BASE_IDS = (
    "neon_blacklight", "neon_cyber_yellow", "neon_dual_glow", "neon_electric_blue",
    "neon_ice_white", "neon_orange_hazard", "neon_pink_blaze", "neon_rainbow_tube",
    "neon_red_alert", "neon_toxic_green",
)
MONOLITHIC_IDS = tuple(fid for fid in NEON_FINISHES if fid not in BASE_IDS)


_ARRAY_CACHE: OrderedDict[str, tuple[np.ndarray, np.ndarray]] = OrderedDict()
_ARRAY_CACHE_LOCK = RLock()


def _authored_arrays(fid: str) -> tuple[np.ndarray, np.ndarray]:
    """Build once per recently used finish; retain only the two shipping arrays.

    Paint and spec execute concurrently in the live compositor. Holding this
    small cold-build lock prevents both threads from building the same 1024px
    PilotResult (and all of its temporary causal masks) at once.
    """
    with _ARRAY_CACHE_LOCK:
        hit = _ARRAY_CACHE.get(fid)
        if hit is not None:
            _ARRAY_CACHE.move_to_end(fid)
            return hit
        module_name, builder_name, _name, _swatch, _desc = NEON_FINISHES[fid]
        result = getattr(import_module(module_name), builder_name)()
        if result.finish_id != fid:
            raise ValueError(f"Neon v4 builder ID drift: expected {fid}, got {result.finish_id}")
        paint = np.ascontiguousarray(np.clip(np.asarray(result.paint, np.float32), 0.0, 1.0))
        spec = np.ascontiguousarray(np.clip(np.asarray(result.spec), 0, 255).astype(np.uint8))
        paint.setflags(write=False)
        spec.setflags(write=False)
        cached = (paint, spec)
        _ARRAY_CACHE[fid] = cached
        while len(_ARRAY_CACHE) > 4:
            _ARRAY_CACHE.popitem(last=False)
        return cached


def _mask2d(mask, fh: int, fw: int) -> np.ndarray:
    m2 = np.asarray(mask, np.float32)
    if m2.ndim == 3:
        m2 = m2[:, :, 0]
    if m2.shape[:2] != (fh, fw):
        m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
    return np.clip(m2, 0.0, 1.0)


def _paint_at(fid: str, fh: int, fw: int) -> np.ndarray:
    paint, _spec = _authored_arrays(fid)
    if paint.shape[:2] == (fh, fw):
        return paint
    return cv2.resize(paint, (fw, fh), interpolation=cv2.INTER_CUBIC)


def _spec_at(fid: str, fh: int, fw: int) -> np.ndarray:
    _paint, spec = _authored_arrays(fid)
    if spec.shape[:2] == (fh, fw):
        return spec
    return cv2.resize(spec, (fw, fh), interpolation=cv2.INTER_NEAREST)


def _make_live_pair(fid: str):
    dependency_modules = (
        NEON_FINISHES[fid][0],
        "engine.expansions.neon_underground_v4.core",
        "engine.expansions.neon_catalog_2026",
    )

    def paint_fn(paint, shape, mask, seed, pm, bb):
        del seed, bb  # Curated per-finish seeds are part of the accepted authored material.
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and float(src.max()) > 1.5:
            src = src / 255.0
        if src.shape[:2] != (fh, fw):
            src = cv2.resize(src, (fw, fh), interpolation=cv2.INTER_LINEAR)
        mix = (_mask2d(mask, fh, fw) * float(pm)).clip(0.0, 1.0)[..., None]
        out = src * (1.0 - mix) + _paint_at(fid, fh, fw) * mix
        return np.clip(out, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        del seed, sm
        fh, fw = int(shape[0]), int(shape[1])
        coverage = _mask2d(mask, fh, fw)[..., None]
        packed = (_spec_at(fid, fh, fw).astype(np.float32) * coverage).clip(0, 255)
        rgba = np.empty((fh, fw, 4), dtype=np.uint8)
        rgba[..., :3] = packed.astype(np.uint8)
        rgba[..., 3] = (coverage[..., 0] * 255.0).clip(0, 255).astype(np.uint8)
        return rgba

    for fn in (paint_fn, spec_fn):
        fn._spb_picker_dependency_modules = dependency_modules
        fn._spb_mono_contract_wrapped = True

    return spec_fn, paint_fn


LIVE_PAIRS = {fid: _make_live_pair(fid) for fid in NEON_FINISHES}


def _base_spec_from_packed(fid: str):
    def base_spec_fn(shape, seed, sm, base_m, base_r, **_kwargs):
        del seed, sm, base_m, base_r
        fh, fw = int(shape[0]), int(shape[1])
        packed = _spec_at(fid, fh, fw)
        return packed[..., 0], packed[..., 1], packed[..., 2]

    base_spec_fn._spb_picker_dependency_modules = (
        NEON_FINISHES[fid][0],
        "engine.expansions.neon_underground_v4.core",
        "engine.expansions.neon_catalog_2026",
    )
    return base_spec_fn


BASE_SPEC_FNS = {fid: _base_spec_from_packed(fid) for fid in BASE_IDS}


def install_base_entries(base_reg) -> int:
    """Replace only the ten compatibility-base contracts, without side effects."""
    count = 0
    for fid in BASE_IDS:
        entry = base_reg.get(fid)
        if not isinstance(entry, dict):
            continue
        _mono_spec, paint_fn = LIVE_PAIRS[fid]
        entry["paint_fn"] = paint_fn
        entry["base_spec_fn"] = BASE_SPEC_FNS[fid]
        entry["desc"] = NEON_FINISHES[fid][4]
        count += 1
    return count


def install_into_engine(mono_reg, base_reg=None, fusion_reg=None):
    """Install the 10 base + 15 monolithic finishes as dead-last live authority."""
    fusion_registries = []
    if fusion_reg is not None:
        fusion_registries.append(fusion_reg)
    try:
        import engine.expansions.fusions as _fus
        fusion_registries.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    try:
        import sys
        legacy = sys.modules.get("shokker_engine_v2")
        if legacy is not None and hasattr(legacy, "FUSION_REGISTRY"):
            fusion_registries.append(legacy.FUSION_REGISTRY)
    except Exception:
        pass

    unique_fusion_registries = []
    seen = set()
    for registry in fusion_registries:
        if registry is not None and id(registry) not in seen:
            unique_fusion_registries.append(registry)
            seen.add(id(registry))
    # Special-group selections deliberately route through mono:<id>, even for
    # the ten compatibility bases. All 25 therefore need monolithic authority.
    for fid in NEON_FINISHES:
        mono_reg[fid] = LIVE_PAIRS[fid]
    for fid in MONOLITHIC_IDS:
        for registry in unique_fusion_registries:
            registry[fid] = LIVE_PAIRS[fid]

    base_count = install_base_entries(base_reg) if base_reg is not None else 0

    return f"neon-underground-v4: {base_count} bases + {len(NEON_FINISHES)} mono routes ({len(MONOLITHIC_IDS)} fusion) live"
