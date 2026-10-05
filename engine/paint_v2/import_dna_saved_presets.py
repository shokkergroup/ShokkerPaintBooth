"""Saved Import DNA recipes — reuse World hits (single / remix / insane quad). SPB-109."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.paint_v2.import_dna_style_catalog import DNA_STYLES
from engine.paint_v2.user_imports_paths import user_imports_root
from engine.paint_v2.user_imports_spec_dna import dna_style_label

PRESETS_FILENAME = "_dna_saved_presets.json"
PRESET_ID_PREFIX = "dna_preset_"


def _presets_path() -> Path:
    root = user_imports_root()
    root.mkdir(parents=True, exist_ok=True)
    return root / PRESETS_FILENAME


def _load() -> Dict[str, Any]:
    path = _presets_path()
    if not path.exists():
        return {"version": 1, "presets": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save(data: Dict[str, Any]) -> None:
    _presets_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def recipe_from_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a World plan row into a storable recipe."""
    kind = plan.get("kind", "style")
    recipe: Dict[str, Any] = {
        "kind": kind,
        "label": plan.get("label", ""),
        "exotic": bool(plan.get("exotic")),
    }
    if kind == "remix":
        recipe["style_a"] = plan["style_a"]
        recipe["style_b"] = plan["style_b"]
        recipe["remix_t"] = float(plan.get("remix_t", 0.5))
    elif kind == "insane":
        recipe["styles"] = list(plan.get("styles", []))
        recipe["weights"] = list(plan.get("weights", []))
    else:
        recipe["style"] = plan.get("style", "abstract_gradient")
    return recipe


def list_saved_presets() -> List[Dict[str, Any]]:
    return list(_load().get("presets", []))


def save_preset(
    recipe: Dict[str, Any],
    *,
    label: Optional[str] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist a DNA recipe for sidebar / future World use."""
    kind = recipe.get("kind", "style")
    if kind == "remix":
        for key in ("style_a", "style_b"):
            if recipe.get(key) not in DNA_STYLES:
                raise ValueError(f"Unknown style: {recipe.get(key)}")
    elif kind == "insane":
        styles = recipe.get("styles") or []
        if len(styles) != 4:
            raise ValueError("INSANE recipe requires exactly 4 styles")
        for sid in styles:
            if sid not in DNA_STYLES:
                raise ValueError(f"Unknown style: {sid}")
    else:
        if recipe.get("style") not in DNA_STYLES:
            raise ValueError(f"Unknown style: {recipe.get('style')}")

    data = _load()
    preset_id = PRESET_ID_PREFIX + uuid.uuid4().hex[:10]
    auto_label = recipe.get("label") or _default_label(recipe)
    row = {
        "id": preset_id,
        "label": (label or auto_label).strip()[:80],
        "recipe": recipe,
        "source": source or "manual",
        "created": datetime.now(timezone.utc).isoformat(),
    }
    data.setdefault("presets", []).append(row)
    _save(data)
    return row


def delete_preset(preset_id: str) -> bool:
    data = _load()
    before = len(data.get("presets", []))
    data["presets"] = [p for p in data.get("presets", []) if p.get("id") != preset_id]
    if len(data["presets"]) == before:
        return False
    _save(data)
    return True


def get_preset(preset_id: str) -> Optional[Dict[str, Any]]:
    for p in list_saved_presets():
        if p.get("id") == preset_id:
            return p
    return None


def _default_label(recipe: Dict[str, Any]) -> str:
    kind = recipe.get("kind", "style")
    if kind == "remix":
        return (
            f"Remix {dna_style_label(recipe['style_a'])} + {dna_style_label(recipe['style_b'])}"
        )
    if kind == "insane":
        names = [dna_style_label(s) for s in recipe.get("styles", [])[:4]]
        return "INSANE · " + " / ".join(names)
    return dna_style_label(str(recipe.get("style", "abstract_gradient")))
