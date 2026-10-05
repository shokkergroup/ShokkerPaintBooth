#!/usr/bin/env python3
"""Sync GRUNGE & FUN into Material World in finish-data (3 copies).

This script is intentionally idempotent: it can repair a stale Cultural
placement, refresh the Material World id list, and rewrite the MONOLITHICS
catalog rows from the current grunge_fun manifest.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GF_MAN = ROOT / "assets" / "reference_textures" / "grunge_fun" / "manifest.json"
JS_FILES = [
    ROOT / "paint-booth-0-finish-data.js",
    ROOT / "electron-app" / "server" / "paint-booth-0-finish-data.js",
    ROOT / "electron-app" / "server" / "pyserver" / "_internal" / "paint-booth-0-finish-data.js",
]
_GF_FALLBACK_DESC = (
    "Grunge & Fun image-authored lacquer with a matched dynamic M/R/Cc spec map "
    "that follows the artwork pattern."
)


def _js_escape_inner(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)[1:-1]


def _gf_ids() -> list[str]:
    if not GF_MAN.exists():
        return []
    data = json.loads(GF_MAN.read_text(encoding="utf-8"))
    return [str(x["id"]) for x in data.get("finishes", []) if x.get("id")]


def _gf_monolithic_lines(finishes: list[dict]) -> list[str]:
    lines = [
        "    // Material World / GRUNGE & FUN - image-authored 2048 plates + matched dynamic spec maps"
    ]
    for f in finishes:
        fid = str(f["id"])
        name = str(f.get("name") or fid)
        desc = (f.get("desc") or _GF_FALLBACK_DESC).strip()
        if not desc.endswith("."):
            desc += "."
        swatch = str(f.get("swatch") or "#57576d").strip()
        lines.append(
            f'    {{ id: "{fid}", name: "{_js_escape_inner(name)}", '
            f'desc: "{_js_escape_inner(desc)}", swatch: "{swatch}" }},'
        )
    return lines


def move(text: str, gf_ids: list[str], gf_lines: list[str]) -> str:
    if not gf_ids:
        return text

    # Remove stale Cultural placement when older scripts put this pack there.
    text = re.sub(
        r'\n    "GRUNGE & FUN": \[[^\]]+\],',
        "",
        text,
        count=1,
    )

    # Replace or add Material World placement.
    mw_entry = f'    "GRUNGE & FUN": {json.dumps(gf_ids)},'
    text, n = re.subn(
        r'    "GRUNGE & FUN": \[[^\]]+\],',
        mw_entry,
        text,
        count=1,
    )
    if n != 1:
        text, n2 = re.subn(
            r"(const _SPECIALS_MATERIAL_WORLD = \{\n)",
            r"\1" + mw_entry + "\n",
            text,
            count=1,
        )
        if n2 != 1:
            raise SystemExit("Could not inject GRUNGE & FUN into _SPECIALS_MATERIAL_WORLD")

    # Section lists: never Cultural, first in Material World.
    text = re.sub(
        r'"Cultural": \["RISING SUN", "VIVA MEXICO", "GRUNGE & FUN", "UNION JACKED"\]',
        '"Cultural": ["RISING SUN", "VIVA MEXICO", "UNION JACKED"]',
        text,
        count=1,
    )
    text = re.sub(
        r'"Material World": \["GRUNGE & FUN", "Atelier',
        '"Material World": ["Atelier',
        text,
        count=1,
    )
    text = re.sub(
        r'"Material World": \["Atelier',
        '"Material World": ["GRUNGE & FUN", "Atelier',
        text,
        count=1,
    )

    # MONOLITHICS: refresh the visible rows from manifest names/descriptions.
    gf_marker = "\n    // Material World / GRUNGE & FUN"
    legacy_gf_marker = "\n    // Cultural / GRUNGE & FUN"
    uj_marker = "\n    // Cultural / UNION JACKED"
    gf_start = text.find(gf_marker)
    if gf_start < 0:
        gf_start = text.find(legacy_gf_marker)
    fresh_block = "\n" + "\n".join(gf_lines) + "\n"
    if gf_start >= 0:
        end = text.find(uj_marker, gf_start)
        if end < 0:
            raise SystemExit("GRUNGE block ordering unexpected")
        text = text[:gf_start] + fresh_block + text[end:]
        return text

    insert_at = text.find(uj_marker)
    if insert_at < 0:
        insert_at = text.find("\n    // Material World /")
    if insert_at < 0:
        raise SystemExit("No insert point for GRUNGE monolithic block")
    return text[:insert_at] + fresh_block + text[insert_at:]


def main() -> None:
    gf_ids = _gf_ids()
    if not gf_ids:
        raise SystemExit(f"No finishes in {GF_MAN}")
    finishes = json.loads(GF_MAN.read_text(encoding="utf-8")).get("finishes") or []
    gf_lines = _gf_monolithic_lines(finishes)

    man = json.loads(GF_MAN.read_text(encoding="utf-8"))
    man["family"] = "Material World"
    GF_MAN.write_text(json.dumps(man, indent=2), encoding="utf-8")

    for js in JS_FILES:
        if not js.exists():
            print("skip", js)
            continue
        text = js.read_text(encoding="utf-8")
        js.write_text(move(text, gf_ids, gf_lines), encoding="utf-8")
        print("synced", js.relative_to(ROOT))


if __name__ == "__main__":
    main()
