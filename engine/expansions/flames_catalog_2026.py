"""FRACTURED FLAMES catalog (2026-06-18) — ADDITIVE expansion registering the 135 validated
flame finishes from engine/paint_v2/flame_spec_recipes.RECIPES into the monolithic registry.

Data-driven (AI-as-compiler): no bespoke per-finish code. For every RECIPES row we register a
(spec_fn, paint_fn) pair built by _mk(), mirroring fractured_themes_2026:
  * PAINT = engine.paint_v2.flame_math.FLAME_STRUCTURES[row['flame']]((H,W), seed) blended onto the
    base via src*(1-kk)+art*kk, kk=clip(mask*pm). Work-res art is lru_cached per fid.
  * SPEC  = the recipe's validated flame_spec mode (ignite/topo/dance) -> HxWx3 uint8 (R=M,G=R,B=Cc),
    iron-safe via flame_spec._finalize, then MASKED (zeroed where mask==0) to honor the booth's
    masked-spec contract (flame_spec returns full-canvas, unlike fracture_spec which takes a mask).

ID SCHEME: fid = "flm_" + recipe_id with "__" -> "_"  ->  f"flm_{flame}_{mode}_{palette}".
3 UI subgroups by mode for browsability: Ignite (51), Topo (35), Dance (49).

ADDITIVE ONLY — does not edit finish-data.js or shokker_engine_v2.py (a later step does shared-file
edits). install_into_engine() registers into mono_reg + the FUSION_REGISTRY mirrors.
"""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

import engine.paint_v2.flame_math as fm
import engine.paint_v2.flame_spec as fs
from engine.paint_v2.flame_spec_recipes import RECIPES

_WORK = 1152

# fid -> recipe row (built at import). fid is collision-free: each row's recipe_id is unique.
FLAME_FINISHES = {("flm_" + r["recipe_id"].replace("__", "_")): r for r in RECIPES}

# Representative swatch hex per palette family (for the JS MONOLITHICS entries).
PALETTE_HEX = {
    "classic": "#ff6a1a", "blue": "#3aa0ff", "violet": "#9a4cff",
    "white_hot": "#ffe8b0", "green_toxic": "#7cff2e", "spectral": "#ff3a8a",
}

# UI subgroups by mode.
GROUP_BASE = "🔥 FRACTURED FLAMES"
SUBGROUPS = {
    "ignite": GROUP_BASE + " · Ignite",
    "topo":   GROUP_BASE + " · Topo",
    "dance":  GROUP_BASE + " · Dance",
}


def _seed_int(seed):
    try:
        return int(seed)
    except Exception:
        return abs(hash(str(seed))) % (2 ** 31)


@lru_cache(maxsize=16)
def _art_work_cached(fid):
    """Work-res PAINT (HxWx3 float 0..1) for a fid, from flame_math only (no spec)."""
    row = FLAME_FINISHES[fid]
    art = np.asarray(fm.FLAME_STRUCTURES[row["flame"]]((_WORK, _WORK), 7), np.float32)
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
    row = FLAME_FINISHES[fid]
    mode = row["mode"]
    palette = row.get("palette", "classic")
    params = dict(row.get("params", {}))

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
        if mode == "ignite":
            kw = {k: params[k] for k in ("frac", "strength") if k in params}
            spec = fs.spec_ignite(art, palette=palette, **kw)
        elif mode == "topo":
            kw = {k: params[k] for k in ("layers",) if k in params}
            spec = fs.spec_topo(art, palette=palette, **kw)
        else:  # dance
            spec = fs.spec_dance(art, palette=palette)
        # MASK the full-canvas spec: only the painted region carries spec.
        spec = np.asarray(spec, np.uint8)
        mm = np.clip(m2, 0.0, 1.0)[..., None]
        return (spec.astype(np.float32) * mm).clip(0, 255).astype(np.uint8)

    return spec_fn, paint_fn


def install_into_engine(mono_reg, base_reg=None):
    """Register every flame finish into the monolithic + UI group-map registries (mirrors FORGE)."""
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
    for fid in FLAME_FINISHES:
        entry = _mk(fid)
        for reg in regs:
            reg[fid] = entry
        n += 1
    counts = {m: sum(1 for r in FLAME_FINISHES.values() if r["mode"] == m) for m in ("ignite", "topo", "dance")}
    csum = ", ".join(f"{m}:{counts[m]}" for m in ("ignite", "topo", "dance"))
    return f"fractured-flames: {n} flame finishes live ({csum})"
