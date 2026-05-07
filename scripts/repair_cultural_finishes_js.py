#!/usr/bin/env python3
"""Restore RISING SUN + VIVA MEXICO in ``paint-booth-0-finish-data.js`` from manifests.

The Union Jacked sync path incorrectly replaced ``_SPECIALS_CULTURAL`` with only
UNION JACKED and dropped RS/VM MONOLITHICS entries at the top of ``MONOLITHICS``.

Run from repo root:
  python scripts/repair_cultural_finishes_js.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RS_MAN = ROOT / "assets" / "reference_textures" / "cultural" / "rising_sun" / "manifest.json"
VM_MAN = ROOT / "assets" / "reference_textures" / "cultural" / "viva_mexico" / "manifest.json"
UJ_MAN = ROOT / "assets" / "reference_textures" / "cultural" / "union_jacked" / "manifest.json"

JS_FILES = [
    ROOT / "paint-booth-0-finish-data.js",
    ROOT / "electron-app" / "server" / "paint-booth-0-finish-data.js",
    ROOT / "electron-app" / "server" / "pyserver" / "_internal" / "paint-booth-0-finish-data.js",
]

_RS_FALLBACK_DESC = (
    "Japanese-inspired cultural lacquer texture with paired dynamic spec detail."
)
_VM_FALLBACK_DESC = (
    "Mexican-inspired cultural lacquer texture with cleaned poster artwork and paired "
    "high-detail spec map depth."
)


def _js_escape_inner(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)[1:-1]


def _texture_path(manifest_entry: dict) -> Path | None:
    tp = manifest_entry.get("texture") or manifest_entry.get("paint")
    sid = str(manifest_entry.get("id") or "")
    if not tp and sid.startswith("rs_"):
        tp = f"assets/reference_textures/cultural/rising_sun/{sid}.png"
    if not tp:
        return None
    s = str(tp).replace("\\", "/")
    if s.startswith("assets/"):
        p = ROOT / s
    elif sid.startswith("rs_"):
        p = ROOT / "assets/reference_textures/cultural/rising_sun" / s
    elif sid.startswith("vm_"):
        p = ROOT / "assets/reference_textures/cultural/viva_mexico" / s
    else:
        p = ROOT / s
    return p if p.exists() else None


def _sample_swatch(path: Path) -> str:
    try:
        im = np.array(Image.open(path).convert("RGB"))
        h, w = im.shape[:2]
        crop = im[int(h * 0.35) : int(h * 0.65), int(w * 0.35) : int(w * 0.65), :]
        mean = crop.reshape(-1, 3).mean(axis=0)
        r, g, b = [int(np.clip(x, 0, 255)) for x in mean]
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return "#57576d"


def _build_finish_lines(
    finishes: list[dict],
    *,
    kind: str,
    fallback_desc: str,
    swatch_from_manifest: bool,
) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    lines: list[str] = []
    comment = (
        "    // Cultural / RISING SUN — image-authored 2048 paint plates with paired dynamic spec maps"
        if kind == "rs"
        else "    // Cultural / VIVA MEXICO — cleaned image-authored 2048 paint plates with paired dynamic spec maps"
    )
    lines.append(comment)

    for f in finishes:
        fid = str(f["id"])
        ids.append(fid)
        name = str(f.get("name") or fid)
        desc = (f.get("desc") or f.get("description") or "").strip()
        if not desc:
            desc = fallback_desc
        elif not desc.endswith("."):
            desc += "."

        swatch = f.get("swatch") if swatch_from_manifest else None
        if swatch:
            swatch = str(swatch).strip()
        if not swatch:
            tp = _texture_path(f)
            swatch = _sample_swatch(tp) if tp else "#57576d"

        lines.append(
            f'    {{ id: "{fid}", name: "{_js_escape_inner(name)}", '
            f'desc: "{_js_escape_inner(desc)}", swatch: "{swatch}" }},'
        )
    return ids, lines


def repair(text: str) -> str:
    rs_data = json.loads(RS_MAN.read_text(encoding="utf-8"))
    vm_data = json.loads(VM_MAN.read_text(encoding="utf-8"))
    rs_finishes = rs_data.get("finishes") or []
    vm_finishes = vm_data.get("finishes") or []

    rs_ids, rs_lines = _build_finish_lines(
        rs_finishes, kind="rs", fallback_desc=_RS_FALLBACK_DESC, swatch_from_manifest=False
    )
    vm_ids, vm_lines = _build_finish_lines(
        vm_finishes,
        kind="vm",
        fallback_desc=_VM_FALLBACK_DESC,
        swatch_from_manifest=True,
    )

    uj_data = json.loads(UJ_MAN.read_text(encoding="utf-8"))
    uj_finishes = uj_data.get("finishes") or []
    uj_ids = [str(x["id"]) for x in uj_finishes]

    cultural_block = (
        "const _SPECIALS_CULTURAL = {\n"
        f'    "RISING SUN": {json.dumps(rs_ids)},\n'
        f'    "VIVA MEXICO": {json.dumps(vm_ids)},\n'
        f'    "UNION JACKED": {json.dumps(uj_ids)},\n'
        "};\n"
    )

    text, n = re.subn(
        r"const _SPECIALS_CULTURAL = \{[\s\S]*?\n\};",
        cultural_block.rstrip("\n"),
        text,
        count=1,
    )
    if n != 1:
        raise SystemExit("Could not replace _SPECIALS_CULTURAL block.")

    text = text.replace(
        '"Cultural": ["UNION JACKED"]',
        '"Cultural": ["RISING SUN", "VIVA MEXICO", "UNION JACKED"]',
        1,
    )

    marker = "\n    // Cultural / UNION JACKED"
    if marker not in text:
        raise SystemExit("Missing UNION JACKED MONOLITHICS marker.")
    uj_start = text.find(marker)

    rs_vm_block = "\n".join(rs_lines + [""] + vm_lines) + "\n"

    rs_marker = "\n    // Cultural / RISING SUN"
    rs_pos = text.rfind(rs_marker, 0, uj_start)
    if rs_pos >= 0:
        text = text[:rs_pos] + "\n" + rs_vm_block + text[uj_start:]
    else:
        text = text[:uj_start] + "\n" + rs_vm_block + text[uj_start:]

    return text


def main() -> None:
    for js in JS_FILES:
        if not js.exists():
            print("skip", js)
            continue
        orig = js.read_text(encoding="utf-8")
        js.write_text(repair(orig), encoding="utf-8")
        print("repaired", js.relative_to(ROOT))


if __name__ == "__main__":
    main()
