# -*- coding: utf-8 -*-
"""Production adapters for owner-reviewable FRACTURED WILDS survivors.

SPB-WILDS rollout tick 2026-08-25. The owner authorized accepted provisional
finishes to be pushed into the experimental app as they clear native-2048
paint, independent material, determinism and performance review. This module
overrides only the IDs in ``ACCEPTED_IDS`` after the legacy 110-ID Wilds
install. Unresolved IDs keep their existing fallback, making rollout additive
and reversible.

Each adapter calls the exact isolated builder that produced the reviewed
native evidence. No shared texture composer, recolor fallback, RNG, noise or
spec substitution is introduced here; this file only provides the monolithic
runtime API, resize/mask handling and a bounded cache.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable

import cv2
import numpy as np


CALM_SPEC = np.asarray((4.0, 120.0, 16.0), np.float32)

ACCEPTED_IDS = (
    "fmo_morpho_blue",
    "fc_webbed_membrane",
    "fpe_amber_plankton",
    "fc_bark_camo",
    "fmo_raven_flash",
    "fpe_violet_garden",
    "fmo_soap_bubble",
    "fmo_monarch_vein",
    "fmo_nacre_brick",
    "fmo_hummingbird_gorget",
    "fmo_scarab_horn",
    "fmo_moonstone_adular",
    "fmo_oil_slick",
    "fmo_fire_agate",
    "fpe_cyan_spineball",
    "fc_feathered_wing",
)


def _float_paint(paint: np.ndarray) -> np.ndarray:
    out = np.asarray(paint)
    if out.ndim != 3 or out.shape[2] < 3:
        raise ValueError(f"accepted Wilds paint must be HxWx3+, got {out.shape}")
    out = out[:, :, :3].astype(np.float32)
    if out.size and float(out.max()) > 1.5:
        out *= np.float32(1.0 / 255.0)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _uint8_spec(spec: np.ndarray) -> np.ndarray:
    out = np.asarray(spec)
    if out.ndim != 3 or out.shape[2] < 3:
        raise ValueError(f"accepted Wilds spec must be HxWx3+, got {out.shape}")
    return np.clip(out[:, :, :3], 0, 255).astype(np.uint8)


@lru_cache(maxsize=4)
def _accepted_authored(fid: str) -> tuple[np.ndarray, np.ndarray]:
    """Build the reviewed A paint and causal M/R/Cc at authored resolution."""
    if fid == "fmo_morpho_blue":
        from . import fractured_wilds_morpho_bio_independent_w2_2026 as module
        paint, spec = module._authored(fid)
    elif fid == "fc_webbed_membrane":
        from . import fractured_wilds_cryptid_rebuild_2026 as module
        paint, spec = module._authored(fid)
    elif fid == "fpe_amber_plankton":
        from . import fractured_wilds_petri_independent_w7_2026 as module
        paint, spec = module._authored(fid)
    elif fid == "fc_bark_camo":
        from . import fractured_wilds_bark_cambium_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_raven_flash":
        from . import fractured_wilds_raven_nematic_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_violet_garden":
        from . import fractured_wilds_violet_growthsheet_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fmo_soap_bubble":
        from . import fractured_wilds_soap_minimal_i1_2026 as module
        fields = module._fields()
        paint = module._compose(fields, module.PALETTE_A, False)
        spec = module._material(fields)
    elif fid == "fmo_monarch_vein":
        from . import fractured_wilds_monarch_vein_i2_2026 as module
        paint, _coverage, maps = module._paint(False)
        spec = module._material(maps)
    elif fid == "fmo_nacre_brick":
        from . import fractured_wilds_nacre_brick_i1_2026 as module
        paint, _coverage, maps = module._paint(False)
        spec = module._material(maps)
    elif fid == "fmo_hummingbird_gorget":
        from . import fractured_wilds_hummingbird_phasefold_i2_2026 as module
        paint, maps = module._optical_sheet(False)
        spec = np.stack(module._spec_maps(maps), axis=2)
    elif fid == "fmo_scarab_horn":
        from . import fractured_wilds_scarab_horn_bouligand_i1_2026 as module
        paint, _coverage, maps = module._paint(False)
        spec = np.stack(module._spec_maps(maps), axis=2)
    elif fid == "fmo_moonstone_adular":
        from . import fractured_wilds_moonstone_adular_relief_i1_2026 as module
        paint, _coverage, maps = module._paint(False)
        spec = np.stack(module._spec_maps(maps), axis=2)
    elif fid == "fmo_oil_slick":
        from . import fractured_wilds_oil_slick_advection_i1_2026 as module
        paint, _coverage, fields = module._paint(False)
        spec = np.stack(module._spec_maps(fields), axis=2)
    elif fid == "fmo_fire_agate":
        from . import fractured_wilds_fire_agate_sheet_i2_2026 as module
        paint, spec = module._authored()
    elif fid == "fpe_cyan_spineball":
        from . import fractured_wilds_cyan_spineball_cage_i1_2026 as module
        paint, spec = module._authored()
    elif fid == "fc_feathered_wing":
        from . import fractured_wilds_feathered_vane_closecrop_i2_2026 as module
        paint, spec = module._authored()
    else:
        raise KeyError(f"Wilds ID is not accepted for runtime override: {fid}")
    paint = _float_paint(paint)
    spec = _uint8_spec(spec)
    if paint.shape[:2] != spec.shape[:2]:
        raise ValueError(f"accepted Wilds paint/spec shape mismatch for {fid}: {paint.shape} vs {spec.shape}")
    return paint, spec


def _zone_mask(mask: np.ndarray, height: int, width: int) -> np.ndarray:
    zone = np.asarray(mask, np.float32)
    if zone.ndim == 3:
        zone = zone[:, :, 0]
    if zone.shape != (height, width):
        zone = cv2.resize(zone, (width, height), interpolation=cv2.INTER_LINEAR)
    return np.clip(zone, 0.0, 1.0)


def _source_paint(paint: np.ndarray, height: int, width: int) -> np.ndarray:
    source = np.asarray(paint, np.float32)
    if source.ndim != 3 or source.shape[2] < 3:
        return np.zeros((height, width, 3), np.float32)
    source = source[:, :, :3]
    if source.size and float(source.max()) > 1.5:
        source = source / np.float32(255.0)
    if source.shape[:2] != (height, width):
        source = cv2.resize(source, (width, height), interpolation=cv2.INTER_LINEAR)
    return np.clip(source, 0.0, 1.0).astype(np.float32)


def _entry(fid: str) -> tuple[Callable, Callable]:
    def paint_fn(paint, shape, mask, seed, pm, bb):
        height, width = int(shape[0]), int(shape[1])
        source = _source_paint(paint, height, width)
        zone = _zone_mask(mask, height, width)
        authored, _spec = _accepted_authored(fid)
        authored = cv2.resize(authored, (width, height), interpolation=cv2.INTER_LANCZOS4)
        alpha = np.clip(zone * max(0.0, float(pm)), 0.0, 1.0)[..., None]
        return np.clip(source * (1.0 - alpha) + authored * alpha, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        height, width = int(shape[0]), int(shape[1])
        zone = _zone_mask(mask, height, width)
        _paint, authored = _accepted_authored(fid)
        authored = cv2.resize(authored, (width, height), interpolation=cv2.INTER_NEAREST).astype(np.float32)
        active = np.clip(CALM_SPEC + (authored - CALM_SPEC) * max(0.0, float(sm)), 0.0, 255.0)
        rgb = active * zone[..., None] + CALM_SPEC * (1.0 - zone[..., None])
        out = np.empty((height, width, 4), np.uint8)
        out[:, :, :3] = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
        out[:, :, 3] = 255
        return out

    paint_fn.__name__ = f"paint_{fid}_accepted_2026"
    spec_fn.__name__ = f"spec_{fid}_accepted_2026"
    return spec_fn, paint_fn


def clear_cache() -> None:
    _accepted_authored.cache_clear()


def install_into_engine(mono_reg, base_reg=None):
    """Override exactly the reviewed Wilds survivors in every live registry."""
    registries = [mono_reg]
    try:
        from engine.expansions import fusions
        registries.append(fusions.FUSION_REGISTRY)
    except Exception:
        pass
    try:
        from engine.registry import FUSION_REGISTRY, MONOLITHIC_REGISTRY
        registries.extend((MONOLITHIC_REGISTRY, FUSION_REGISTRY))
    except Exception:
        pass
    import sys
    engine = sys.modules.get("shokker_engine_v2")
    if engine is not None and hasattr(engine, "FUSION_REGISTRY"):
        registries.append(engine.FUSION_REGISTRY)
    unique = []
    for registry in registries:
        if all(registry is not other for other in unique):
            unique.append(registry)
    for fid in ACCEPTED_IDS:
        entry = _entry(fid)
        for registry in unique:
            registry[fid] = entry
    return f"fractured-wilds-accepted: {len(ACCEPTED_IDS)} native-reviewed experimental overrides live"


__all__ = ["ACCEPTED_IDS", "clear_cache", "install_into_engine"]
