#!/usr/bin/env python3
"""Collapse SPEC_PATTERN_GROUPS + SPEC_PATTERNS.category to 14 review lanes in finish-data."""
from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "_workbook_metrics" / "spec_patterns_catalog.json"

MEGA_MAP = {
    "Structure": "Structure & Geometry",
    "Metallic": "Sparkle & Micro-Metal",
    "Coating": "Clearcoat & Coating",
    "Texture": "Surface & Spray Texture",
    "Weathering": "Weather, Wear & Track",
    "Optical": "Optical & Interference",
    "Organic": "Organic & Natural",
    "Sparkle": "Sparkle & Micro-Metal",
    "Brushed": "Directional Metal & Brush",
    "Guilloché": "Precision & Guilloché",
    "Guilloche": "Precision & Guilloché",
    "Carbon & Weave": "Carbon & Composite Weave",
    "Geometric": "Structure & Geometry",
    "Natural": "Organic & Natural",
    "Clearcoat": "Clearcoat & Coating",
    "Surface Treatment": "Surface & Spray Texture",
    "Exotic": "Exotic & Kinetic",
    "Racing": "Racing & Livery Story",
    "Sponsor & Vinyl": "Racing & Livery Story",
    "Race Wear": "Weather, Wear & Track",
    "Premium": "Sparkle & Micro-Metal",
    "Race Heritage": "Racing & Livery Story",
    "Mechanical": "Mechanical & Industrial",
    "Weather & Track": "Weather, Wear & Track",
    "Artistic": "Artistic & Abstract",
    "Abstract Art": "Artistic & Abstract",
    "Crystalline": "Sparkle & Micro-Metal",
    "Kinetic": "Exotic & Kinetic",
    "Misc": "Structure & Geometry",
}

MEGA_ORDER = [
    "Sparkle & Micro-Metal",
    "Optical & Interference",
    "Directional Metal & Brush",
    "Carbon & Composite Weave",
    "Clearcoat & Coating",
    "Structure & Geometry",
    "Surface & Spray Texture",
    "Organic & Natural",
    "Weather, Wear & Track",
    "Racing & Livery Story",
    "Mechanical & Industrial",
    "Exotic & Kinetic",
    "Precision & Guilloché",
    "Artistic & Abstract",
]

OWNER_HERO_IDS = ("pearl_micro", "crystal_shimmer", "crushed_glass")

TARGETS = [
    ROOT / "paint-booth-0-finish-data.js",
    ROOT / "electron-app" / "server" / "paint-booth-0-finish-data.js",
    ROOT / "electron-app" / "server" / "pyserver" / "_internal" / "paint-booth-0-finish-data.js",
]


def lane_for_legacy_category(cat: str) -> str:
    if cat in MEGA_ORDER:
        return cat
    return MEGA_MAP.get(cat, "Artistic & Abstract")


def parse_groups_block(text: str) -> dict[str, list[str]]:
    m = re.search(r"const SPEC_PATTERN_GROUPS = \{", text)
    if not m:
        raise RuntimeError("SPEC_PATTERN_GROUPS not found")
    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    block = text[start : i - 1]
    groups: dict[str, list[str]] = {}
    for gm in re.finditer(r'"([^"]+)":\s*\[([^\]]*)\]', block, re.S):
        groups[gm.group(1)] = re.findall(r'"([^"]+)"', gm.group(2))
    return groups


def load_catalog() -> dict[str, str]:
    rows = json.loads(CATALOG.read_text(encoding="utf-8"))
    return {r["id"]: r["category"] for r in rows}


def sort_ids(ids: list[str]) -> list[str]:
    heroes = [x for x in OWNER_HERO_IDS if x in ids]
    rest = sorted(x for x in ids if x not in OWNER_HERO_IDS)
    return heroes + rest


def build_mega_groups(pattern_cats: dict[str, str]) -> dict[str, list[str]]:
    mega: dict[str, list[str]] = defaultdict(list)
    for pid, cat in pattern_cats.items():
        mega[lane_for_legacy_category(cat)].append(pid)
    return {lane: sort_ids(ids) for lane in MEGA_ORDER if (ids := mega.get(lane))}


def format_groups(groups: dict[str, list[str]]) -> str:
    lines = [
        "// =============================================================================",
        "// SPEC PATTERN GROUPS — sub-tab navigation for SPEC_PATTERNS picker",
        "// 2026-05-17: Consolidated 27+ legacy tabs -> 14 review lanes (SPB_SPEC_PATTERNS_ATLAS).",
        "// =============================================================================",
        "const SPEC_PATTERN_GROUPS = {",
    ]
    for lane in MEGA_ORDER:
        ids = groups.get(lane, [])
        if not ids:
            continue
        lines.append(f'    "{lane}": [')
        for pid in ids:
            lines.append(f'        "{pid}",')
        lines[-1] = lines[-1].rstrip(",")
        lines.append("    ],")
    if lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]
    lines.append("};")
    lines.append("")
    lines.append("// Explicit picker tab order (Object.keys order is reliable in modern engines; this documents intent).")
    lines.append("const SPEC_PATTERN_GROUP_ORDER = " + json.dumps(MEGA_ORDER, ensure_ascii=False) + ";")
    return "\n".join(lines) + "\n"


def update_categories(text: str, pattern_cats: dict[str, str]) -> str:
    id_mega = {pid: lane_for_legacy_category(cat) for pid, cat in pattern_cats.items()}

    def repl_line(line: str) -> str:
        mid = re.search(r'id:\s*"([^"]+)"', line)
        if not mid or "category:" not in line:
            return line
        mega = id_mega.get(mid.group(1))
        if not mega:
            return line
        return re.sub(r'category:\s*"[^"]*"', f'category: "{mega}"', line)

    m = re.search(r"const SPEC_PATTERNS = \[", text)
    if not m:
        return text
    start = m.start()
    end = text.find("\n];", m.end()) + 3
    block = text[start:end]
    return text[:start] + "\n".join(repl_line(ln) for ln in block.splitlines()) + text[end:]


def replace_groups_section(text: str, new_section: str) -> str:
    m = re.search(r"// =+\n// SPEC PATTERN GROUPS", text)
    if not m:
        m = re.search(r"const SPEC_PATTERN_GROUPS = \{", text)
    start = m.start() if m else text.index("const SPEC_PATTERN_GROUPS")
    m_end = re.search(r"\n// =+\n// GROUP MAPS", text[start:])
    if not m_end:
        raise RuntimeError("GROUP MAPS anchor not found")
    end = start + m_end.start() + 1
    return text[:start] + new_section + text[end:]


def apply_file(path: Path, pattern_cats: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    old_groups = parse_groups_block(text)
    if set(old_groups) <= set(MEGA_ORDER) and len(old_groups) >= 10:
        print(f"{path.name}: already consolidated ({len(old_groups)} lanes), skip")
        return
    mega_groups = build_mega_groups(pattern_cats)
    text = replace_groups_section(text, format_groups(mega_groups))
    text = update_categories(text, pattern_cats)
    path.write_text(text, encoding="utf-8")
    total = sum(len(v) for v in mega_groups.values())
    print(f"{path.name}: {len(old_groups)} tabs -> {len(mega_groups)} lanes, {total} patterns")


def main() -> None:
    pattern_cats = load_catalog()
    apply_file(TARGETS[0], pattern_cats)
    for dest in TARGETS[1:]:
        shutil.copy2(TARGETS[0], dest)
        print(f"  synced -> {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
