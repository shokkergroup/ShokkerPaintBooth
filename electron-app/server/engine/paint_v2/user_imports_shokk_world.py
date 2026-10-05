"""SHOKK THE WORLD — 20-variant Import DNA explosion (SPB-109).

8 standard + 7 two-style remix + 5 INSANE four-style blends per run.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from engine.paint_v2.user_imports_ingest import (
    _read_manifest,
    _write_manifest,
    normalize_paint_image,
    slugify,
    swatch_hex,
    unique_finish_id,
)
from engine.paint_v2.user_imports_paths import CANVAS_SIZE, ID_PREFIX
from engine.paint_v2.user_imports_paths import user_imports_root
from engine.paint_v2.import_dna_style_catalog import (
    DNA_STYLES,
    WORLD_SLOT_INSANE,
    WORLD_SLOT_REMIX,
    WORLD_SLOT_STANDARD,
    WORLD_VARIANT_COUNT,
    is_exotic_style,
    pick_diverse_pairs,
    pick_insane_quads,
    spread_styles_excluding,
)
from engine.paint_v2.import_dna_saved_presets import recipe_from_plan
from engine.paint_v2.user_imports_spec_dna import (
    bake_import_spec_dna,
    bake_import_spec_dna_insane,
    bake_import_spec_dna_remix,
    classify_style_from_image,
    dna_metadata,
    dna_style_label,
    make_import_preview_payload,
    pil_to_data_url,
    spec_to_rgb_preview,
)

STAGING_ID_PREFIX = "ui_stw_"
SESSION_DIR = "_shokk_world_sessions"
# Long INSANE/remix bakes must not block the Flask worker (Try in Booth / next slot).
_BAKE_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="spb_stw_bake")


def _sessions_root() -> Path:
    root = user_imports_root() / SESSION_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def _session_path(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")[:64]
    return _sessions_root() / safe


def _remix_partners(auto_style: str) -> List[str]:
    from engine.paint_v2.import_dna_style_catalog import remix_partners_for

    return remix_partners_for(auto_style)


def resolve_remix_styles(
    auto_style: str,
    remix_style_a: Optional[str] = None,
    remix_style_b: Optional[str] = None,
) -> Tuple[str, str]:
    """Pick TWO DIFFERENT DNA styles for the sidebar DNA Remix slot.

    Style A defaults to the requested style (or Auto). Style B defaults to the
    first remix partner — but is ALWAYS forced to differ from A so the remix
    never bakes the same style twice (e.g. Halftone Hex + Halftone Hex).
    """
    auto = auto_style if auto_style in DNA_STYLES else "abstract_gradient"
    ra = remix_style_a if remix_style_a in DNA_STYLES else auto
    partners = _remix_partners(auto)
    if remix_style_b in DNA_STYLES:
        rb = remix_style_b
    else:
        rb = partners[0] if partners else auto
    if rb == ra:
        rb = next((p for p in partners if p != ra), rb)
    if rb == ra:
        rb = next((sid for sid in DNA_STYLES if sid != ra), rb)
    return ra, rb


def plan_world_variants(
    auto_style: str,
    *,
    remix_style_a: Optional[str] = None,
    remix_style_b: Optional[str] = None,
    remix_t: float = 0.5,
    session_seed: int = 0,
) -> List[Dict[str, Any]]:
    """8 standard · 7 remix · 5 INSANE (four-style random blend)."""
    plans: List[Dict[str, Any]] = []
    auto = auto_style if auto_style in DNA_STYLES else "abstract_gradient"
    spread = spread_styles_excluding(
        auto, WORLD_SLOT_STANDARD - 1, prefer_exotic=3, seed=session_seed ^ 0x5350
    )

    plans.append({
        "index": 0,
        "kind": "hero",
        "style": auto,
        "label": f"Auto · {dna_style_label(auto)}",
        "max_passes": 2,
        "micro_seed": 88001,
        "exotic": is_exotic_style(auto),
        "bake_index": 1,
        "alive": True,
    })

    for i, style in enumerate(spread):
        plans.append({
            "index": len(plans),
            "kind": "standard",
            "style": style,
            "label": dna_style_label(style),
            "max_passes": 1,
            "micro_seed": 91000 + i * 997,
            "exotic": is_exotic_style(style),
            "bake_index": 10 + i * 6,
            "alive": True,
        })

    pairs = pick_diverse_pairs(
        auto,
        WORLD_SLOT_REMIX,
        seed=session_seed ^ 0xE0111C,
    )
    ra, rb = resolve_remix_styles(auto, remix_style_a, remix_style_b)
    # Only first mix slot uses sidebar DNA Remix; others are cross-catalog pairs (not all Auto+X).
    if pairs:
        pairs[0] = (ra, rb, float(remix_t))

    for j, (sa, sb, t) in enumerate(pairs):
        plans.append({
            "index": len(plans),
            "kind": "remix",
            "style_a": sa,
            "style_b": sb,
            "remix_t": t,
            "label": f"Mix · {dna_style_label(sa)} + {dna_style_label(sb)}",
            "max_passes": 1,
            "micro_seed": 93000 + j * 503,
            "exotic": False,
            "bake_index": 200 + j * 11,
            "alive": True,
        })

    quads = pick_insane_quads(WORLD_SLOT_INSANE, seed=session_seed ^ 0x1A54EE)
    for k, (styles, weights) in enumerate(quads):
        short = " / ".join(dna_style_label(s).split()[0] for s in styles[:4])
        plans.append({
            "index": len(plans),
            "kind": "insane",
            "styles": styles,
            "weights": weights,
            "label": f"INSANE · {short}",
            "max_passes": 1,
            "micro_seed": 96000 + k * 7919,
            "exotic": True,
            "bake_index": 400 + k * 29,
            "alive": True,
            "preview_fast": True,
        })

    return plans[:WORLD_VARIANT_COUNT]


def start_shokk_world_session(
    paint: Image.Image,
    display_name: str,
    *,
    vibe_ref: Optional[str] = None,
    remix_style_a: Optional[str] = None,
    remix_style_b: Optional[str] = None,
    remix_t: float = 0.5,
    chroma_scale: float = 1.0,
    palette_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Normalize paint to 2048² and create session manifest (variants generated lazily)."""
    session_id = uuid.uuid4().hex[:12]
    sp = _session_path(session_id)
    sp.mkdir(parents=True, exist_ok=True)
    (sp / "variants").mkdir(exist_ok=True)

    paint_norm = normalize_paint_image(paint)
    paint_norm.save(sp / "paint.png", "PNG", optimize=True)

    auto_style, analysis = classify_style_from_image(paint_norm, display_name)
    session_seed = int(hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:12], 16)
    plans = plan_world_variants(
        auto_style,
        remix_style_a=remix_style_a,
        remix_style_b=remix_style_b,
        remix_t=remix_t,
        session_seed=session_seed,
    )

    meta = {
        "session_id": session_id,
        "name": display_name,
        "vibe_ref": vibe_ref,
        "auto_style": auto_style,
        "session_seed": session_seed,
        "chroma_scale": max(0.3, min(1.8, float(chroma_scale))),
        "palette_overrides": palette_overrides or {},
        "plan_layout": {
            "standard": WORLD_SLOT_STANDARD,
            "remix": WORLD_SLOT_REMIX,
            "insane": WORLD_SLOT_INSANE,
        },
        "analysis": {
            "style": analysis.style,
            "material_hint": analysis.material_hint,
            "confidence": round(analysis.confidence, 3),
        },
        "remix": dict(zip(("style_a", "style_b"), resolve_remix_styles(auto_style, remix_style_a, remix_style_b))) | {"t": remix_t},
        "total": WORLD_VARIANT_COUNT,
        "generated": 0,
        "plans": plans,
        "created": datetime.now(timezone.utc).isoformat(),
    }
    (sp / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    thumb = paint_norm.resize((384, 384), Image.Resampling.LANCZOS)
    return {
        "session_id": session_id,
        "total": WORLD_VARIANT_COUNT,
        "name": display_name,
        "auto_style": auto_style,
        "auto_style_label": dna_style_label(auto_style),
        "preview_paint": pil_to_data_url(thumb),
        "plan_layout": meta["plan_layout"],
        "plans": [{"index": p["index"], "label": p["label"], "kind": p["kind"]} for p in plans],
    }


def _bake_plan(
    paint: Image.Image,
    name: str,
    plan: Dict[str, Any],
    vibe_ref: Optional[str],
    *,
    full_gauntlet: bool = False,
    chroma_scale: float = 1.0,
    palette_overrides=None,
) -> Tuple[Image.Image, dict]:
    """Execute one variant plan → spec + dna metadata."""
    kind = plan.get("kind", "style")
    max_passes = int(plan.get("max_passes", 2))
    if full_gauntlet:
        max_passes = max(max_passes, 5)
    micro_seed = int(plan.get("micro_seed", 88001))
    exotic = bool(plan.get("exotic"))
    bake_index = int(plan.get("bake_index", 1))
    alive = bool(plan.get("alive", True))

    if kind == "insane":
        result = bake_import_spec_dna_insane(
            paint,
            name,
            plan.get("styles", []),
            plan.get("weights", []),
            vibe_ref=vibe_ref,
            micro_seed=micro_seed,
            bake_index=bake_index,
            preview_fast=bool(plan.get("preview_fast")) and not full_gauntlet,
            chroma_scale=chroma_scale,
            palette_overrides=palette_overrides,
        )
    elif kind == "remix":
        result = bake_import_spec_dna_remix(
            paint,
            name,
            plan["style_a"],
            plan["style_b"],
            float(plan.get("remix_t", 0.5)),
            vibe_ref=vibe_ref,
            max_gauntlet_passes=max_passes,
            micro_seed=micro_seed,
            exotic=exotic,
            bake_index=bake_index,
            alive=alive,
            chroma_scale=chroma_scale,
            palette_overrides=palette_overrides,
        )
    else:
        style = plan.get("style", "abstract_gradient")
        result = bake_import_spec_dna(
            paint,
            name,
            vibe_ref=vibe_ref,
            style_override=style,
            max_gauntlet_passes=max_passes,
            micro_seed=micro_seed,
            exotic=exotic,
            bake_index=bake_index,
            alive=alive,
            chroma_scale=chroma_scale,
            palette_overrides=palette_overrides,
        )
    spec = result.spec
    meta = dna_metadata(result)
    meta["variant_kind"] = kind
    if plan.get("label"):
        meta["variant_label"] = plan["label"]
    elif kind == "remix":
        meta["variant_label"] = f"{plan.get('style_a', '')}+{plan.get('style_b', '')}"
    elif kind == "insane":
        meta["variant_label"] = "insane"
    else:
        meta["variant_label"] = str(plan.get("style", "abstract_gradient"))
    meta["exotic_amp"] = exotic
    meta["dna_recipe"] = recipe_from_plan(plan)
    if kind == "remix":
        meta["remix"] = {
            "style_a": plan["style_a"],
            "style_b": plan["style_b"],
            "t": plan.get("remix_t"),
        }
    elif kind == "insane":
        meta["insane"] = {
            "styles": plan.get("styles"),
            "weights": plan.get("weights"),
        }
    return spec, meta


def _generate_world_variant_impl(session_id: str, index: int) -> Dict[str, Any]:
    """Bake + preview payload (runs in worker thread for long slots)."""
    sp = _session_path(session_id)
    meta_path = sp / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Session not found: {session_id}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    plans = meta.get("plans", [])
    if index < 0 or index >= len(plans):
        raise IndexError(f"Variant index out of range: {index}")

    plan = plans[index]
    out_spec = sp / "variants" / f"{index:02d}_spec.png"
    out_meta = sp / "variants" / f"{index:02d}.json"

    if out_spec.exists() and out_meta.exists():
        spec_img = Image.open(out_spec)
        vmeta = json.loads(out_meta.read_text(encoding="utf-8"))
    else:
        paint = Image.open(sp / "paint.png")
        name = meta.get("name", "shokk_world")
        try:
            spec_img, vmeta = _bake_plan(
                paint,
                f"{name}_{index}",
                plan,
                meta.get("vibe_ref"),
                full_gauntlet=False,
                chroma_scale=float(meta.get("chroma_scale", 1.0)),
                palette_overrides=meta.get("palette_overrides"),
            )
            spec_img.save(out_spec, "PNG", optimize=True)
            out_meta.write_text(json.dumps(vmeta, indent=2), encoding="utf-8")
            meta["generated"] = max(int(meta.get("generated", 0)), index + 1)
            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        except Exception as exc:
            if out_spec.exists():
                out_spec.unlink()
            if out_meta.exists():
                out_meta.unlink()
            raise RuntimeError(f"Variant {index + 1} bake failed: {exc}") from exc

    paint = Image.open(sp / "paint.png")
    thumb = 320
    previews = make_import_preview_payload(paint, spec_img, thumb=thumb)
    spec_only = spec_to_rgb_preview(spec_img).resize((thumb, thumb), Image.Resampling.LANCZOS)
    kind = plan.get("kind", "style")

    return {
        "index": index,
        "label": plan.get("label", vmeta.get("variant_label", "")),
        "kind": kind,
        "dna": vmeta,
        "dna_recipe": vmeta.get("dna_recipe") or recipe_from_plan(plan),
        "preview_spec": previews["preview_spec"],
        "preview_combined": pil_to_data_url(spec_only),
        "gauntlet_passed": vmeta.get("gauntlet_passed", False),
        "exotic_amp": bool(vmeta.get("exotic_amp")),
        "is_insane": kind == "insane",
    }


def generate_world_variant(session_id: str, index: int) -> Dict[str, Any]:
    """Generate variant `index` if missing; return preview payload."""
    future = _BAKE_EXECUTOR.submit(_generate_world_variant_impl, session_id, index)
    return future.result(timeout=900)


def reroll_world_variant(session_id: str, index: int) -> Dict[str, Any]:
    """SPB-109 (2026-05-29): rebake ONE slot with a fresh seed for a new take.

    Keeps the slot's style/kind identity but reshuffles the seed (and re-rolls the
    remix partner / insane quad so mixes feel genuinely different), then drops the
    cached spec and regenerates just that variant.
    """
    sp = _session_path(session_id)
    meta_path = sp / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Session not found: {session_id}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    plans = meta.get("plans", [])
    if index < 0 or index >= len(plans):
        raise IndexError(f"Variant index out of range: {index}")

    plan = plans[index]
    roll = int(plan.get("reroll", 0)) + 1
    plan["reroll"] = roll
    bump = (roll * 0x9E37 + index * 0x2545) & 0xFFFFF
    plan["micro_seed"] = int(plan.get("micro_seed", 88001)) ^ bump
    plan["bake_index"] = int(plan.get("bake_index", 1)) + roll * 13
    kind = plan.get("kind")
    reroll_seed = (meta.get("session_seed", 0) ^ (index * 0x51ED) ^ (roll * 0xB17E))

    if kind == "remix":
        pairs = pick_diverse_pairs(meta.get("auto_style", "abstract_gradient"), 7, seed=reroll_seed)
        if pairs:
            sa, sb, t = pairs[roll % len(pairs)]
            plan["style_a"], plan["style_b"], plan["remix_t"] = sa, sb, t
            plan["label"] = f"Mix · {dna_style_label(sa)} + {dna_style_label(sb)}"
    elif kind == "insane":
        quads = pick_insane_quads(5, seed=reroll_seed)
        if quads:
            styles, weights = quads[roll % len(quads)]
            plan["styles"], plan["weights"] = styles, weights
            short = " / ".join(dna_style_label(s).split()[0] for s in styles[:4])
            plan["label"] = f"INSANE · {short}"

    meta["plans"][index] = plan
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    for suffix in (f"{index:02d}_spec.png", f"{index:02d}.json"):
        fp = sp / "variants" / suffix
        if fp.exists():
            fp.unlink()

    return generate_world_variant(session_id, index)


def preview_dna_remix(
    session_id: str,
    style_a: str,
    style_b: str,
    remix_t: float,
) -> Dict[str, Any]:
    """Live DNA remix preview against session paint (does not persist)."""
    sp = _session_path(session_id)
    if not (sp / "paint.png").exists():
        raise FileNotFoundError(f"Session not found: {session_id}")
    paint = Image.open(sp / "paint.png")
    name = json.loads((sp / "meta.json").read_text(encoding="utf-8")).get("name", "remix")
    vibe_ref = json.loads((sp / "meta.json").read_text(encoding="utf-8")).get("vibe_ref")
    result = bake_import_spec_dna_remix(
        paint,
        name + "_remix",
        style_a,
        style_b,
        remix_t,
        vibe_ref=vibe_ref,
        max_gauntlet_passes=2,
    )
    previews = make_import_preview_payload(paint, result.spec, thumb=384)
    return {
        "preview_spec": previews["preview_spec"],
        "style_a": style_a,
        "style_b": style_b,
        "remix_t": remix_t,
    }


def commit_world_variants(
    session_id: str,
    indices: List[int],
    *,
    name_prefix: Optional[str] = None,
    run_full_gauntlet: bool = True,
) -> List[dict]:
    """Commit selected session variants as permanent ui_* library entries."""
    sp = _session_path(session_id)
    if not (sp / "paint.png").exists():
        raise FileNotFoundError(f"Session not found: {session_id}")

    meta = json.loads((sp / "meta.json").read_text(encoding="utf-8"))
    paint = Image.open(sp / "paint.png")
    base_name = (name_prefix or meta.get("name") or "Shokk World").strip()
    root = user_imports_root()
    root.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest(root)
    imported: List[dict] = []

    for idx in sorted(set(indices)):
        if idx < 0 or idx >= WORLD_VARIANT_COUNT:
            continue
        generate_world_variant(session_id, idx)
        spec_path = sp / "variants" / f"{idx:02d}_spec.png"
        vmeta_path = sp / "variants" / f"{idx:02d}.json"
        if not spec_path.exists():
            continue

        plan = meta["plans"][idx]
        label = plan.get("label", f"Variant {idx + 1}")
        entry_name = f"{base_name} · {label}"[:80]
        finish_id = unique_finish_id(root, slugify(entry_name), manifest)

        paint_out = root / f"{finish_id}.png"
        if not paint_out.exists():
            paint.save(paint_out, "PNG", optimize=True)

        spec_img = Image.open(spec_path)
        if run_full_gauntlet:
            vibe_ref = meta.get("vibe_ref")
            spec_img, vmeta = _bake_plan(
                paint,
                entry_name,
                plan,
                vibe_ref,
                full_gauntlet=True,
                chroma_scale=float(meta.get("chroma_scale", 1.0)),
                palette_overrides=meta.get("palette_overrides"),
            )
        else:
            vmeta = json.loads(vmeta_path.read_text(encoding="utf-8"))

        spec_img.save(root / f"{finish_id}_spec.png", "PNG", optimize=True)
        entry = {
            "id": finish_id,
            "name": entry_name,
            "kind": "paint_monolithic",
            "spec_mode": "auto_dna",
            "swatch": swatch_hex(paint),
            "imported": datetime.now(timezone.utc).isoformat(),
            "source_file": "shokk_the_world",
            "import_dna": vmeta,
            "dna_recipe": vmeta.get("dna_recipe") or recipe_from_plan(plan),
            "shokk_world_session": session_id,
            "shokk_world_index": idx,
        }
        manifest.setdefault("entries", []).append(entry)
        imported.append(entry)

    _write_manifest(root, manifest)
    return imported


def stage_variant_for_booth(
    session_id: str,
    index: int,
    *,
    use_paint_source: bool = True,
) -> dict:
    """Register a temporary ui_stw_* finish for Paint Booth / iRacing try-before-save.

    use_paint_source=True (default): SHOKK DROP upload becomes zone paint + spec (matches World bake).
    use_paint_source=False: spec only (dna_plate), truck TGA paint unchanged.
    """
    sp = _session_path(session_id)
    spec_cached = sp / "variants" / f"{index:02d}_spec.png"
    if not spec_cached.exists():
        raise ValueError(
            "This variant is still baking — wait for its preview to appear before Try in Booth."
        )
    meta = json.loads((sp / "meta.json").read_text(encoding="utf-8"))
    plan = meta["plans"][index]
    label = plan.get("label", f"Preview {index + 1}")
    base = meta.get("name", "Shokk World")

    root = user_imports_root()
    root.mkdir(parents=True, exist_ok=True)
    manifest = _read_manifest(root)
    sid_short = session_id[:8]
    finish_id = f"{STAGING_ID_PREFIX}{sid_short}_{index:02d}"

    manifest["entries"] = [
        e for e in manifest.get("entries", [])
        if not (str(e.get("id", "")).startswith(f"{STAGING_ID_PREFIX}{sid_short}"))
    ]

    spec_img = Image.open(sp / "variants" / f"{index:02d}_spec.png")
    spec_img.save(root / f"{finish_id}_spec.png", "PNG", optimize=True)
    session_paint = Image.open(sp / "paint.png")
    session_paint.save(root / f"{finish_id}.png", "PNG", optimize=True)

    vmeta = json.loads((sp / "variants" / f"{index:02d}.json").read_text(encoding="utf-8"))
    # Always dna_plate so booth spec matches World thumbnail; paint toggled via use_paint_source.
    spec_mode = "dna_plate"
    staged_booth = not use_paint_source

    entry = {
        "id": finish_id,
        "name": f"{base} · {label} (preview)"[:80],
        "kind": "paint_monolithic",
        "spec_mode": spec_mode,
        "staged_booth": staged_booth,
        "use_paint_source": use_paint_source,
        "swatch": swatch_hex(session_paint),
        "imported": datetime.now(timezone.utc).isoformat(),
        "staging": True,
        "shokk_world_session": session_id,
        "shokk_world_index": index,
        "import_dna": vmeta,
        "dna_recipe": vmeta.get("dna_recipe"),
    }
    manifest.setdefault("entries", []).append(entry)
    _write_manifest(root, manifest)
    return {"id": finish_id, "name": entry["name"], "index": index}


def purge_staging_for_session(session_id: str) -> int:
    """Remove temporary booth preview entries."""
    root = user_imports_root()
    manifest = _read_manifest(root)
    sid_short = session_id[:8]
    prefix = f"{STAGING_ID_PREFIX}{sid_short}"
    removed = 0
    kept = []
    for e in manifest.get("entries", []):
        eid = str(e.get("id", ""))
        if eid.startswith(prefix):
            removed += 1
            for suffix in ("", "_spec", "_preview"):
                p = root / f"{eid}{suffix}.png"
                if p.exists():
                    p.unlink()
            continue
        kept.append(e)
    if removed:
        manifest["entries"] = kept
        _write_manifest(root, manifest)
    return removed


def get_dna_style_list() -> List[dict]:
    from engine.paint_v2.user_imports_spec_dna import get_dna_style_catalog

    return get_dna_style_catalog()
