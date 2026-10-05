#!/usr/bin/env python3
"""Refresh display names in grunge_fun/manifest.json without rebuilding plates."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / "assets" / "reference_textures" / "grunge_fun" / "manifest.json"


def _load_builder():
    path = ROOT / "scripts" / "build_cultural_grunge_fun.py"
    spec = importlib.util.spec_from_file_location("build_cultural_grunge_fun", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    mod = _load_builder()
    data = json.loads(MAN.read_text(encoding="utf-8"))
    finishes = data.get("finishes") or []
    for index, entry in enumerate(finishes, start=1):
        src = entry.get("source") or ""
        stem = Path(src).stem
        finish_id = str(entry.get("id") or "")
        style = str(entry.get("style") or "grunge_scratch")
        style = mod.curated_style(finish_id, stem, index)
        name = mod.title_from_stem(stem, style, index, finish_id)
        entry["style"] = style
        entry["name"] = name
        entry["desc"] = mod.desc_for_finish(name, finish_id, style)
        entry["tags"] = mod.tags_for_finish(finish_id, style)
    MAN.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"updated {len(finishes)} names in {MAN}")


if __name__ == "__main__":
    main()
