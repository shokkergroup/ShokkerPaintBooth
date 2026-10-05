#!/usr/bin/env python3
"""SPB-102/PRISM — wire Spectrum Shift + PRISM FORGE into paint-booth-0-finish-data.js (3 copies)."""
from __future__ import annotations

import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TARGETS = [
    ROOT / "paint-booth-0-finish-data.js",
    ROOT / "electron-app/server/paint-booth-0-finish-data.js",
    ROOT / "electron-app/server/pyserver/_internal/paint-booth-0-finish-data.js",
]

PALETTES = [
    "oil_slick", "aurora", "sunset", "vapor", "holographic",
    "goldsmith", "phantom", "inferno", "mirage", "reptile",
]
VARIANTS = ["classic", "macro", "micro", "shimmer", "wave"]


def _title(s: str) -> str:
    return s.replace("_", " ").title()


def _pf_name(desc: str, fid: str) -> str:
    if desc.startswith("PRISM FORGE "):
        chunk = desc.split("—", 1)[0].replace("PRISM FORGE ", "").strip()
        if chunk:
            return f"PF: {chunk}"
    return f"PF: {_title(fid.replace('pf_', ''))}"


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_fragments() -> dict[str, str]:
    from engine.paint_v2.prism_forge import _PF_ROWS

    pf_ids = [r["id"] for r in _PF_ROWS]
    base_lines = []
    for r in _PF_ROWS:
        fid = r["id"]
        desc = r.get("desc", "PRISM FORGE spectral base.")
        base_lines.append(
            f'    {{ id: "{fid}", name: "{_esc(_pf_name(desc, fid))}", '
            f'desc: "{_esc(desc)}", swatch: "#888899" }},'
        )

    spectrum_ids = [f"spectrum_{p}_{v}" for p in PALETTES for v in VARIANTS]
    mono_lines = []
    for sid in spectrum_ids:
        pal, var = sid.replace("spectrum_", "").rsplit("_", 1)
        name = f"Spectrum {_title(pal)} {_title(var)}"
        desc = (
            f"SPB-102 ★ Spectrum Shift — { _title(pal) } palette, { var } variant. "
            "Chromatic substrate + facet spec iridescence."
        )
        mono_lines.append(
            f'    {{ id: "{sid}", name: "{_esc(name)}", desc: "{_esc(desc)}", swatch: "#6677aa" }},'
        )

    pf_group = json.dumps(pf_ids)
    spec_group = json.dumps(spectrum_ids)

    return {
        "bases_block": "\n".join([
            "    // SPB-102 / PRISM FORGE — procedural spectral bases (2026-05-17 UI wire-up)",
            *base_lines,
        ]),
        "monos_block": "\n".join([
            "    // SPB-102 ★ Spectrum Shift — 50 procedural iridescent fusions (2026-05-17 UI wire-up)",
            *mono_lines,
        ]),
        "pf_group": pf_group,
        "spec_group": spec_group,
    }


def patch_file(path: Path, frags: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    if "pf_event_horizon_spectra" in text and "spectrum_oil_slick_classic" in text:
        print(f"skip (already wired): {path}")
        return

    if "SPB-102 / PRISM FORGE" not in text:
        anchor = '    { id: "living_matte", name: "Living Matte"'
        if anchor not in text:
            raise RuntimeError(f"BASES anchor missing in {path}")
        text = text.replace(
            anchor,
            frags["bases_block"] + "\n" + anchor,
            1,
        )

    if "SPB-102 ★ Spectrum Shift" not in text:
        anchor = '    { id: "quilt_organic_cells", name: "Quilt Organic Cells"'
        if anchor not in text:
            raise RuntimeError(f"MONOLITHICS anchor missing in {path}")
        text = text.replace(
            anchor,
            frags["monos_block"] + "\n" + anchor,
            1,
        )

    if '"★ PRISM FORGE"' not in text:
        text = text.replace(
            '"Paint Technique": ["paint_drip_gravity"',
            '"★ PRISM FORGE": ' + frags["pf_group"] + ',\n    "Paint Technique": ["paint_drip_gravity"',
            1,
        )

    if '"★ Spectrum Shift"' not in text:
        text = text.replace(
            '"Panel Quilting": ["quilt_alternating_duo"',
            '"★ Spectrum Shift": ' + frags["spec_group"] + ',\n    "Panel Quilting": ["quilt_alternating_duo"',
            1,
        )
        text = text.replace(
            '"Fusion Lab": ["Ghost Geometry"',
            '"Fusion Lab": ["★ Spectrum Shift", "Ghost Geometry"',
            1,
        )

    path.write_text(text, encoding="utf-8")
    print(f"patched: {path}")


def main() -> None:
    frags = build_fragments()
    for t in TARGETS:
        if not t.is_file():
            raise SystemExit(f"missing: {t}")
        patch_file(t, frags)


if __name__ == "__main__":
    main()
