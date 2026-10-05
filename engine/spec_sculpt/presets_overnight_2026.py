"""Spec Sculpt — FRACTURED catalog mirror (additive, 2026-06-18).

DOCTRINE (owner): anything that enters or is redone in the SPB catalog must "follow suit" in the
other sides of the app. So Spec Sculpt now mirrors the WHOLE FRACTURED procedural library — not a
hand-picked subset. This module AUTO-ENUMERATES every FRACTURED finish from the live registry and
registers each as a Spec Sculpt material preset, grouped by family. New FRACTURED finishes added to
the catalog later show up here automatically (no hand-editing).

FRACTURED is procedural (no reference-texture plates) so it resolves for every buyer. Image-backed
packs (Forbidden Dragon `fd_*`, Mortal/Money Shokk, ColorShoxx, Grunge, Guest Designers) are
EXCLUDED — they'd fail to resolve without their plates. Not a replacement for the sacred SHOKK DROP
exact-import path (this is material *suggestion/blend*, never spec authoring).
"""
from __future__ import annotations

# Procedural FRACTURED family prefixes → Spec Sculpt category. (fd_ = Forbidden Dragon, image-backed → excluded.)
_FRACTURED_FAMILIES = {
    "ff_": "Fractured Forge",
    "fm_": "Fractured Minds",
    "fs_": "Fractured Souls",
    "fc_": "Fractured Cryptid",
    "fu_": "Fractured UFO",
    "fr_": "Fractured Rainbow",
    "fo_": "Fractured Occult",
}

_registered = False
_count = 0


def _label_for(fid: str, prefix: str) -> str:
    name = fid[len(prefix):].replace("_", " ").strip()
    return " ".join(w.capitalize() for w in name.split()) or fid


def _tags_for(fid: str, prefix: str, category: str) -> list:
    fam = category.split()[-1].lower()
    toks = [t for t in fid[len(prefix):].split("_") if t]
    return [fam] + toks[:3]


def register(verify_resolve: bool = False) -> int:
    """Mirror the full FRACTURED library into SPEC_SCULPT_PRESETS. Idempotent.

    Enumerates the merged (FRACTURED-inclusive) monolithic registry and adds a preset for every
    FRACTURED-family finish not already present/used. Fast (registry enumeration only — no rendering
    at import). All FRACTURED finishes were verified to resolve via the spec-sculpt path; a finish
    that somehow doesn't simply fails gracefully in the lab. Returns the number added.
    """
    global _registered, _count
    if _registered:
        return _count
    import engine.spec_sculpt.presets as P
    try:
        from engine.spec_sculpt.catalog_blend import _full_monolithic_registry
        merged = _full_monolithic_registry() or {}
    except Exception:
        merged = {}

    existing_slugs = {str(p["id"]) for p in P.SPEC_SCULPT_PRESETS}
    used_finishes = {fid for pr in P.SPEC_SCULPT_PRESETS for fid, _ in pr["catalog"]}

    # Fractured Deep shares the fd_ prefix with the image-backed Forbidden Dragon pack, so it can't
    # be matched by prefix. Pull its EXPLICIT id-set from the themes module and include only those
    # (procedural), leaving the rest of fd_ (Forbidden Dragon, plate-dependent) excluded.
    deep_ids = set()
    try:
        import engine.expansions.fractured_themes_2026 as _T
        deep_ids = set(getattr(_T, "DEEP", {}).keys())
    except Exception:
        deep_ids = set()

    added = 0

    def _add(fid, category, prefix):
        nonlocal added
        slug = "ov_" + fid
        if slug in existing_slugs or fid in used_finishes or fid not in merged:
            return
        label = _label_for(fid, prefix)
        P.SPEC_SCULPT_PRESETS.append(
            P._p(slug, label, category, fid, f"{label} — {category} material.", _tags_for(fid, prefix, category)))
        existing_slugs.add(slug)
        used_finishes.add(fid)
        added += 1

    for fid in sorted(merged.keys()):
        prefix = next((px for px in _FRACTURED_FAMILIES if fid.startswith(px)), None)
        if prefix is not None:
            _add(fid, _FRACTURED_FAMILIES[prefix], prefix)

    for fid in sorted(deep_ids):
        _add(fid, "Fractured Deep", "fd_")

    P.VALID_SPEC_SCULPT_PRESET_IDS = frozenset(str(p["id"]) for p in P.SPEC_SCULPT_PRESETS)
    P.PRESET_CATALOG_BY_ID = {str(p["id"]): list(p["catalog"]) for p in P.SPEC_SCULPT_PRESETS}
    P.PRESET_TILE_BY_ID = {
        str(p["id"]): float(P.PRESET_TILE_OVERRIDE.get(str(p["id"]), 1.0)) for p in P.SPEC_SCULPT_PRESETS
    }
    _registered = True
    _count = added
    return added
