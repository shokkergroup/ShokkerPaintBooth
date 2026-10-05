"""Auto-tagger for SPB finish data.

Reads `paint-booth-0-finish-data.js` (lightly — no JS parser required, just regex
extraction of id/name/desc/category triples) and emits `paint-booth-0-finish-tags.js`
containing a `FINISH_TAGS` dict keyed by finish id with an `Array<string>` of tags.

The tag taxonomy is documented in `_loop_state/tag_taxonomy.md`. This script
matches finish names + descriptions against that taxonomy's keyword map and
seeds tags from the group label / id prefix.

Usage:
    python scripts/build_finish_tags.py

This is intentionally additive — it produces a new dict, it doesn't mutate any
existing data file. The 3-copy mirror is performed by the script.

Owner (2026-05-27) directive: every finish needs SOME tags. Untagged finishes
are flagged so the owner can do a manual pass later.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "paint-booth-0-finish-data.js"
OUT_NAME = "paint-booth-0-finish-tags.js"
MIRROR_DIRS = [
    ROOT,
    ROOT / "electron-app" / "server",
    ROOT / "electron-app" / "server" / "pyserver" / "_internal",
]

# ----------------------------------------------------------------------------
# Tag taxonomy: keyword -> tag(s). Match is case-insensitive substring over
# (name + " " + desc). When the keyword fires, every tag in the value list is
# appended to the finish's tag set.
#
# Keep this list curated — broad enough to cover the catalog but not so noisy
# that every finish ends up with 30 tags.
# ----------------------------------------------------------------------------
TAG_KEYWORDS: dict[str, list[str]] = {
    # --- Color family ---
    "red": ["red"],
    "crimson": ["red"],
    "scarlet": ["red"],
    "ruby": ["red"],
    "blood": ["red"],
    "cherry": ["red"],
    "blue": ["blue"],
    "navy": ["blue"],
    "azure": ["blue"],
    "cobalt": ["blue"],
    "sapphire": ["blue"],
    "teal": ["blue", "green"],
    "cyan": ["blue", "cyan"],
    "green": ["green"],
    "emerald": ["green"],
    "lime": ["green"],
    "olive": ["green"],
    "forest": ["green"],
    "jade": ["green"],
    "purple": ["purple"],
    "violet": ["purple"],
    "amethyst": ["purple"],
    "lavender": ["purple"],
    "magenta": ["purple", "pink"],
    "pink": ["pink"],
    "rose": ["pink"],
    "copper": ["copper", "metallic", "warm"],
    "bronze": ["copper", "metallic", "warm"],
    "brass": ["gold", "metallic", "warm"],
    "gold": ["gold", "metallic", "warm"],
    "amber": ["gold", "warm"],
    "honey": ["gold", "warm"],
    "silver": ["silver", "metallic"],
    "platinum": ["silver", "metallic", "luxury"],
    "titanium": ["silver", "metallic"],
    "pewter": ["silver", "metallic"],
    "black": ["black"],
    "obsidian": ["black"],
    "onyx": ["black"],
    "raven": ["black"],
    "midnight": ["black"],
    "white": ["white"],
    "ivory": ["white"],
    "pearl": ["white", "pearl"],
    "snow": ["white"],
    "grey": ["grey"],
    "gray": ["grey"],
    "graphite": ["grey", "black"],
    "charcoal": ["grey", "black"],
    "gunmetal": ["grey", "black", "metallic"],
    "orange": ["orange", "warm"],
    "tangerine": ["orange", "warm"],
    "yellow": ["yellow", "warm"],
    "neon": ["neon", "bright"],
    "rainbow": ["multicolor", "iridescent"],
    "iridescent": ["iridescent", "multicolor"],
    "holographic": ["holographic", "iridescent", "multicolor"],
    "prism": ["iridescent", "multicolor"],
    "prizm": ["iridescent", "multicolor"],
    "chromatic": ["iridescent", "multicolor"],
    "spectrum": ["iridescent", "multicolor"],
    "spectral": ["iridescent", "multicolor"],
    # --- Material / finish ---
    "metallic": ["metallic"],
    "metal flake": ["metallic", "flake"],
    "flake": ["flake", "metallic"],
    "sparkle": ["sparkle", "flake"],
    "glitter": ["sparkle", "flake"],
    "shimmer": ["shimmer"],
    "candy": ["candy", "deep"],
    "carbon": ["carbon"],
    "kevlar": ["carbon", "aramid"],
    "aramid": ["aramid"],
    "weave": ["weave", "carbon"],
    "forged": ["carbon", "forged"],
    "chrome": ["chrome", "metallic", "reflective"],
    "mirror": ["chrome", "reflective"],
    "ceramic": ["ceramic"],
    "glass": ["glass"],
    "crystal": ["glass", "iridescent"],
    "satin": ["satin"],
    "matte": ["matte"],
    "flat": ["matte"],
    "gloss": ["gloss"],
    "wet": ["gloss"],
    "vinyl": ["vinyl"],
    "wrap": ["vinyl"],
    "anodized": ["anodized"],
    # --- Style / mood ---
    "racing": ["racing"],
    "race": ["racing"],
    "luxury": ["luxury"],
    "premium": ["luxury"],
    "executive": ["luxury"],
    "military": ["military", "tactical"],
    "tactical": ["tactical"],
    "stealth": ["stealth", "tactical", "matte"],
    "camo": ["military", "tactical"],
    "camouflage": ["military", "tactical"],
    "vintage": ["vintage", "retro"],
    "retro": ["retro"],
    "antique": ["vintage"],
    "modern": ["modern"],
    "futuristic": ["futuristic", "cyber"],
    "cyber": ["cyber", "futuristic"],
    "neon ": ["neon", "cyber"],
    "gothic": ["gothic", "dark"],
    "horror": ["gothic", "dark"],
    "graveyard": ["gothic", "dark"],
    "industrial": ["industrial"],
    "organic": ["organic"],
    "alien": ["alien", "futuristic"],
    "showroom": ["showroom", "luxury"],
    "drift": ["drift", "racing"],
    "off road": ["offroad"],
    "off-road": ["offroad"],
    "muddy": ["offroad", "weathered"],
    "mud": ["offroad", "weathered"],
    # --- Texture ---
    "smooth": ["smooth"],
    "rough": ["rough"],
    "hammered": ["hammered"],
    "brushed": ["brushed"],
    "weathered": ["weathered"],
    "distressed": ["weathered", "distressed"],
    "aged": ["weathered", "vintage"],
    "patina": ["weathered", "vintage"],
    "rust": ["weathered", "rust"],
    "polished": ["polished"],
    "scratched": ["weathered", "distressed"],
    # --- Theme ---
    "fire": ["fire"],
    "flame": ["fire"],
    "lava": ["fire"],
    "molten": ["fire"],
    "ember": ["fire"],
    "ice": ["ice", "cold"],
    "frost": ["ice", "cold"],
    "frozen": ["ice", "cold"],
    "water": ["water"],
    "ocean": ["water"],
    "wave": ["water"],
    "tide": ["water"],
    "marine": ["water"],
    "storm": ["weather"],
    "weather": ["weather"],
    "lightning": ["lightning", "weather"],
    "aurora": ["aurora", "iridescent"],
    "galaxy": ["space", "futuristic"],
    "nebula": ["space", "futuristic"],
    "solar": ["space", "fire"],
    "sun": ["fire"],
    "sunrise": ["sunset", "warm"],
    "sunset": ["sunset", "warm"],
    "predator": ["predator-skin", "organic"],
    "snake": ["predator-skin", "organic"],
    "scale": ["scales", "organic"],
    "feather": ["organic"],
    "beetle": ["organic", "iridescent"],
    "insect": ["organic", "iridescent"],
    "anime": ["anime", "cultural"],
    "manga": ["anime", "cultural"],
    "kanji": ["anime", "cultural"],
    "aztec": ["cultural"],
    "talavera": ["cultural"],
    "luchador": ["cultural"],
    "mexico": ["cultural"],
    "japan": ["cultural"],
    "japanese": ["cultural"],
    "tribal": ["cultural"],
    "celtic": ["cultural"],
    # --- Use case ---
    "tank": ["military"],
    "armor": ["military", "tactical"],
    "battleship": ["military"],
    "police": ["emergency"],
    "ambulance": ["emergency"],
    "emergency": ["emergency"],
    "barn": ["weathered", "vintage"],
    # --- Era (decade callouts) ---
    "50s": ["era-50s", "retro"],
    "60s": ["era-60s", "retro"],
    "70s": ["era-70s", "retro"],
    "80s": ["era-80s", "retro"],
    "90s": ["era-90s", "retro"],
    "muscle": ["muscle", "retro"],
    "hot rod": ["retro"],
}

# ID-prefix seeds: certain id namespaces always get these tags.
ID_PREFIX_TAGS: dict[str, list[str]] = {
    "p_": ["paradigm", "showcase"],
    "vm_": ["viva-mexico", "cultural", "showcase"],
    "pf_": ["prism-forge", "showcase"],
    "rs_": ["rising-sun", "cultural"],
    "csx_": ["colorshoxx", "showcase"],
    "cs_": ["colorshoxx", "showcase"],
    "anime_": ["anime", "cultural"],
    "beetle_": ["organic", "iridescent"],
    "carbon_": ["carbon"],
    "candy_": ["candy", "deep"],
    "chrome_": ["chrome", "metallic", "reflective"],
}

# Group label hints: substring match on group name -> tags.
GROUP_LABEL_TAGS: dict[str, list[str]] = {
    "luxury": ["luxury"],
    "premium": ["luxury"],
    "metallic standard": ["metallic"],
    "foundation": ["base"],
    "chrome": ["chrome", "metallic", "reflective"],
    "pearl": ["pearl"],
    "candy": ["candy", "deep"],
    "matte": ["matte"],
    "satin": ["satin"],
    "carbon": ["carbon"],
    "weather": ["weathered"],
    "rust": ["weathered", "rust"],
    "anime": ["anime", "cultural"],
    "shokk": ["showcase"],
    "colorshoxx": ["colorshoxx", "showcase"],
    "prizm": ["iridescent"],
    "iridescent": ["iridescent"],
    "insect": ["organic", "iridescent"],
    "viva": ["cultural"],
    "rising sun": ["cultural"],
    "mortal": ["showcase"],
    "neon": ["neon", "bright"],
    "spectral": ["iridescent"],
    "vision": ["iridescent"],
    "fractal": ["futuristic"],
    "physics": ["showcase"],
    "showcase": ["showcase"],
    "military": ["military", "tactical"],
    "tactical": ["tactical"],
    "racing": ["racing"],
    "horror": ["gothic", "dark"],
    "predator": ["predator-skin", "organic"],
}


# ----------------------------------------------------------------------------
# Light JS parser: pull {id, name, desc, ...} object literals from the source
# without trying to evaluate the whole file. We only need name/desc text for
# keyword matching, so a regex over each object literal is enough.
# ----------------------------------------------------------------------------
ENTRY_RE = re.compile(
    r"\{\s*id:\s*\"(?P<id>[^\"]+)\"[^}]*?name:\s*\"(?P<name>[^\"]*)\"[^}]*?desc:\s*\"(?P<desc>[^\"]*)\"",
    re.DOTALL,
)


def parse_finishes(text: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for m in ENTRY_RE.finditer(text):
        fid = m.group("id")
        if fid in seen:
            continue
        seen.add(fid)
        out.append({"id": fid, "name": m.group("name"), "desc": m.group("desc")})
    return out


# ----------------------------------------------------------------------------
# Tag derivation
# ----------------------------------------------------------------------------
def derive_tags(entry: dict[str, str]) -> list[str]:
    fid = entry["id"]
    hay = (entry["name"] + " " + entry["desc"]).lower()
    tags: set[str] = set()

    # ID prefix seeds
    for prefix, prefix_tags in ID_PREFIX_TAGS.items():
        if fid.startswith(prefix):
            tags.update(prefix_tags)

    # Keyword matches
    for kw, kw_tags in TAG_KEYWORDS.items():
        if kw in hay:
            tags.update(kw_tags)

    # Sort for stable output
    return sorted(tags)


def coverage_stats(tagged: dict[str, list[str]]) -> dict[str, int]:
    buckets = {"zero": 0, "one_to_three": 0, "four_plus": 0}
    for tags in tagged.values():
        n = len(tags)
        if n == 0:
            buckets["zero"] += 1
        elif n <= 3:
            buckets["one_to_three"] += 1
        else:
            buckets["four_plus"] += 1
    return buckets


def emit_js(tagged: dict[str, list[str]]) -> str:
    lines = [
        "// ============================================================",
        "// PAINT-BOOTH-0-FINISH-TAGS.JS - Auto-generated smart tags",
        "// ============================================================",
        "// Generated by scripts/build_finish_tags.py.",
        "// Do NOT hand-edit this file unless you're recording an owner-",
        "// approved override. Re-run the script to regenerate.",
        "//",
        "// FINISH_TAGS[finishId] -> Array<string> of canonical tags.",
        "// The fuzzy search layer in paint-booth-2-state-zones.js looks",
        "// these up additively — finishes get found by typing tag terms",
        "// (e.g. 'metallic', 'luxury', 'racing', 'red').",
        "// ============================================================",
        "",
        "const FINISH_TAGS = {",
    ]
    for fid in sorted(tagged.keys()):
        tags = tagged[fid]
        tags_js = ", ".join(json.dumps(t) for t in tags)
        lines.append(f"    {json.dumps(fid)}: [{tags_js}],")
    lines.append("};")
    lines.append("")
    lines.append("if (typeof window !== 'undefined') { window.FINISH_TAGS = FINISH_TAGS; }")
    lines.append("if (typeof module !== 'undefined' && module.exports) { module.exports = FINISH_TAGS; }")
    lines.append("")
    return "\n".join(lines)


def md5(path: Path) -> str:
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    if not SRC.exists():
        print(f"ERROR: source file missing: {SRC}", file=sys.stderr)
        return 1
    text = SRC.read_text(encoding="utf-8", errors="replace")
    entries = parse_finishes(text)
    print(f"Parsed {len(entries)} finish entries from {SRC.name}")

    tagged: dict[str, list[str]] = {}
    for e in entries:
        tagged[e["id"]] = derive_tags(e)

    stats = coverage_stats(tagged)
    print(f"Tag coverage:")
    print(f"  0 tags:    {stats['zero']:4d}")
    print(f"  1-3 tags:  {stats['one_to_three']:4d}")
    print(f"  4+ tags:   {stats['four_plus']:4d}")

    untagged = [fid for fid, tags in tagged.items() if not tags]
    if untagged:
        print(f"\nFinishes with ZERO tags (need owner manual pass, {len(untagged)} total):")
        for fid in untagged[:25]:
            print(f"  - {fid}")
        if len(untagged) > 25:
            print(f"  ... and {len(untagged) - 25} more")

    js = emit_js(tagged)
    primary = MIRROR_DIRS[0] / OUT_NAME
    primary.write_text(js, encoding="utf-8")
    print(f"\nWrote {primary} ({len(js)} bytes)")

    # Mirror to all 3 locations
    for mirror_dir in MIRROR_DIRS[1:]:
        mirror_dir.mkdir(parents=True, exist_ok=True)
        dest = mirror_dir / OUT_NAME
        shutil.copy2(primary, dest)
        print(f"Mirrored -> {dest}")

    # Verify md5 of all three mirrors
    print("\nMirror md5 verification:")
    for mirror_dir in MIRROR_DIRS:
        p = mirror_dir / OUT_NAME
        print(f"  {md5(p)}  {p}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
