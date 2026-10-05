"""MATERIALS & PHYSICS catalog (2026-06-19) — ADDITIVE expansion registering the 8 reworked
materials finishes (engine/paint_v2/materials_math.MATERIALS_STRUCTURES) into the monolithic
registry. Total rework of the old Material-Gradients / Exotic-Physics colour swaps -> 8 real
fabricated MATERIAL surfaces (carbon twill / forged carbon / engine-turning / liquid metal /
crystal lattice / ferrofluid / fracture net / damascus steel).

UNLIKE neon/anime/optics (emissive art -> flame_spec), materials are METALS: the spec is the
dedicated materials_math.material_spec() (physically-metallic, structure-tracing, iron-safe) with a
per-finish MATERIAL_SPEC_PARAMS entry giving a diverse mirror->satin metal family.
ADDITIVE ONLY — shared-file edits (finish-data.js / shokker_engine_v2) happen separately.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

import engine.paint_v2.materials_math as mat

_WORK = 1152
GROUP = "★ MATERIALS & PHYSICS"

# fid -> (structure, display name, swatch hex, description)
MATERIALS_FINISHES = {
    "materials2_carbon":   ("carbon_twill",   "Carbon Twill Weave",  "#2a3142", "A true 2/2 twill carbon-fibre weave — interlacing tows, diagonal rib, fine carbon filaments."),
    "materials2_forged":   ("forged_carbon",  "Forged Carbon",       "#4a4e57", "Marbled chopped-carbon composite — flake shards at random fibre angles with micro glints in resin."),
    "materials2_engine":   ("engine_turned",  "Engine-Turned Metal", "#9094a0", "Machined jeweling — overlapping domed swirls of fine concentric brush rings on polished metal."),
    "materials2_liquid":   ("liquid_metal",   "Liquid Metal",        "#aeb6c4", "Flowing chrome / mercury — a reflective metaball surface with mirror bands and capillary ripples."),
    "materials2_crystal":  ("crystal_lattice","Crystal Lattice",     "#7a82a0", "A grown mineral bed — faceted crystal grains with bright cleavage edges and pin-point glints."),
    "materials2_ferro":    ("ferrofluid",     "Ferrofluid Spikes",   "#14161c", "Ferrofluid under a magnet — the Rosensweig spike lattice, black iron mounds with glossy steel caps."),
    "materials2_fracture": ("fracture_net",   "Fracture Net",        "#42454c", "A stressed brittle surface shattered into a bright crack network over subtly tilted plates."),
    "materials2_damascus": ("damascus_steel", "Damascus Steel",      "#5a5d62", "Pattern-welded Damascus — folded layers of light/dark steel ground back into a flowing watermark."),
    "materials2_kevlar":   ("kevlar_aramid",  "Kevlar Aramid Weave", "#b88c1e", "Golden aramid basket-weave — pairs of tows woven two-at-a-time with fine aramid filaments."),
    "materials2_titanium": ("anodized_titanium", "Anodized Titanium","#5a4a8a", "Heat-tinted titanium — straw / violet / cobalt / cyan oxide colours flowing over fine ground metal."),
    "materials2_meteorite": ("meteorite_widmanstatten", "Meteorite Widmanstatten", "#7d8088", "Etched iron-meteorite — interlocking kamacite ribbons crossing at the octahedrite angles."),
}


@lru_cache(maxsize=16)
def _art_work_cached(fid):
    structure = MATERIALS_FINISHES[fid][0]
    art = np.asarray(mat.MATERIALS_STRUCTURES[structure]((_WORK, _WORK), 7), np.float32)
    if art.ndim == 2:
        art = np.repeat(art[..., None], 3, axis=2)
    art = art[:, :, :3]
    if art.size and art.max() > 1.5:
        art = art / 255.0
    return np.clip(art, 0.0, 1.0)


def _mask2d(mask, fh, fw):
    m2 = np.asarray(mask, np.float32)
    if m2.ndim == 3:
        m2 = m2[:, :, 0]
    if m2.shape[:2] != (fh, fw):
        m2 = cv2.resize(m2, (fw, fh), interpolation=cv2.INTER_LINEAR)
    return m2


def _mk(fid):
    structure = MATERIALS_FINISHES[fid][0]
    spec_params = mat.MATERIAL_SPEC_PARAMS[structure]

    def paint_fn(paint, shape, mask, seed, pm, bb):
        fh, fw = int(shape[0]), int(shape[1])
        src = np.asarray(paint, np.float32)[:, :, :3]
        if src.size and src.max() > 1.5:
            src = src / 255.0
        m2 = _mask2d(mask, fh, fw)
        art = cv2.resize(_art_work_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        kk = np.clip(m2 * float(pm), 0.0, 1.0)[..., None]
        out = src * (1.0 - kk) + art * kk
        return np.clip(out, 0.0, 1.0).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        fh, fw = int(shape[0]), int(shape[1])
        m2 = _mask2d(mask, fh, fw)
        art = cv2.resize(_art_work_cached(fid), (fw, fh), interpolation=cv2.INTER_LINEAR)
        spec = np.asarray(mat.material_spec(art, **spec_params), np.uint8)
        mm = np.clip(m2, 0.0, 1.0)[..., None]
        return (spec.astype(np.float32) * mm).clip(0, 255).astype(np.uint8)

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Register every materials finish into the monolithic + FUSION registries (mirrors optics_catalog)."""
    regs = [mono_reg]
    try:
        import engine.expansions.fusions as _fus
        regs.append(_fus.FUSION_REGISTRY)
    except Exception:
        pass
    import sys as _sys
    _eng = _sys.modules.get("shokker_engine_v2")
    if _eng is not None and hasattr(_eng, "FUSION_REGISTRY"):
        regs.append(_eng.FUSION_REGISTRY)
    n = 0
    for fid in MATERIALS_FINISHES:
        entry = _mk(fid)
        for reg in regs:
            reg[fid] = entry
        n += 1
    return f"materials-physics: {n} reworked material finishes live"
