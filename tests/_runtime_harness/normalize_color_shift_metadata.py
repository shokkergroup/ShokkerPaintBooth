"""HEENAN HSIG-CX-1/2/3 — COLORSHOXX honesty pass.

Three-part fix to the COLORSHOXX picker presentation. All three are about
honesty: making the picker disagree with itself less.

(1) cs_* MONOLITHIC overlay presets (27 entries) had ZERO entries in
    FINISH_METADATA. They surfaced in the Specials tab with default
    sortPriority 50 and no family/section tagging — orphans next to the
    cx_* heroes, diluting the COLORSHOXX brand.

(2) Three of the 27 cs_* names collided directly with cx_* heroes:
       cs_inferno  vs  cx_inferno
       cs_supernova vs cx_supernova
       cs_oilslick  vs cx_oil_slick
    Painter clicks "Inferno" twice, gets two visibly different finishes.
    Disambiguate by appending the engine type to the cs_* display name.

(3) Three cx_* Wave-2 chrome-vs-matte entries are pure engine clones of
    cx_chrome_void with only color RGB changing (audited 2026-04-20):
       cx_rose_chrome
       cx_blood_mercury
       cx_toxic_chrome
    Mark each as advanced=true so the default Materials tab surfaces the
    distinct cx_chrome_void / cx_neon_abyss / cx_obsidian_gold /
    cx_electric_storm / cx_midnight_chrome / cx_white_lightning /
    cx_glacier_fire as the seven hero chrome flips.

Idempotent — re-runs produce no changes.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

METADATA_PATHS = [
    REPO / "paint-booth-0-finish-metadata.js",
    REPO / "electron-app" / "server" / "paint-booth-0-finish-metadata.js",
    REPO / "electron-app" / "server" / "pyserver" / "_internal" / "paint-booth-0-finish-metadata.js",
]
DATA_PATHS = [
    REPO / "paint-booth-0-finish-data.js",
    REPO / "electron-app" / "server" / "paint-booth-0-finish-data.js",
    REPO / "electron-app" / "server" / "pyserver" / "_internal" / "paint-booth-0-finish-data.js",
]

# (1) The 27 cs_* MONOLITHIC overlay presets (id, friendly section).
CS_OVERLAY_IDS = [
    "cs_complementary", "cs_cool", "cs_deepocean", "cs_extreme", "cs_inferno",
    "cs_mystichrome", "cs_nebula", "cs_rainbow", "cs_solarflare", "cs_split",
    "cs_subtle", "cs_supernova", "cs_toxic", "cs_triadic",
    "cs_candy_paint", "cs_dark_flame", "cs_gold_rush", "cs_oilslick",
    "cs_rose_gold_shift", "cs_warm",
    "cs_chrome_shift", "cs_earth", "cs_monochrome", "cs_neon_shift",
    "cs_ocean_shift", "cs_prism_shift", "cs_vivid",
]

# (2) Display-name disambiguation in MONOLITHICS.
CS_NAME_FIXES = [
    # (id, old name, new name, reason)
    ("cs_inferno",   "CS Inferno",      "CS Inferno (Overlay Shift)",      "name collided with cx_inferno hero"),
    ("cs_supernova", "CS Supernova",    "CS Supernova (Overlay Shift)",    "name collided with cx_supernova hero"),
    ("cs_oilslick",  "CS Oil Slick",    "CS Oil Slick (Overlay Shift)",    "name collided with cx_oil_slick hero"),
    ("cs_mystichrome", "CS Mystichrome", "CS Mystichrome (Purple\u2192Green Overlay)", "Mystichrome IS purple\u2192green; clarify it's the overlay version"),
]

# (3) cx_* engine-clone demotions (set advanced=true).
CX_DEMOTE_IDS = [
    "cx_rose_chrome",
    "cx_blood_mercury",
    "cx_toxic_chrome",
]


def _replace_value(body, key, new_value):
    if isinstance(new_value, bool):
        v = "true" if new_value else "false"
    elif isinstance(new_value, str):
        v = json.dumps(new_value)
    else:
        v = str(new_value)
    pat = re.compile(r'"' + re.escape(key) + r'":\s*("[^"]*"|true|false|-?\d+)')
    if pat.search(body):
        replacement = f'"{key}": {v}'
        return pat.sub(lambda _m, _r=replacement: _r, body), True
    body = body.rstrip()
    if body.endswith(","):
        body = body[:-1]
    body += f',\n    "{key}": {v}\n  '
    return body, True


def _block_re(entry_id):
    return re.compile(
        r'(  "' + re.escape(entry_id) + r'":\s*\{)([^}]*)(\})',
        re.MULTILINE | re.DOTALL,
    )


def _ensure_cs_metadata(text):
    """Insert a metadata block for each cs_* id that lacks one.

    Block placement: append into the dedicated HSIG-CX-1 block at the end
    of FINISH_METADATA so we don't disturb the auto-generated alphabetical
    ordering of the rest of the file.
    """
    inserted = []
    skipped_present = []
    for cid in CS_OVERLAY_IDS:
        if _block_re(cid).search(text):
            skipped_present.append(cid)
            continue
        inserted.append(cid)

    if not inserted:
        return text, [], skipped_present

    # Build the block.
    parts = [
        "\n",
        "  // 2026-04-20 HEENAN HSIG-CX-1 \u2014 27 cs_* color-shift overlay\n",
        "  // presets shipped with ZERO FINISH_METADATA. Default sortPriority 50\n",
        "  // surfaced them next to cx_* heroes in the Specials tab, diluting the\n",
        "  // COLORSHOXX brand. Tag them as Color Shift Overlay family with\n",
        "  // sortPriority 60 so cx_* heroes (80) keep top billing while the\n",
        "  // overlay presets remain accessible and properly searchable.\n",
    ]
    for cid in inserted:
        block = (
            f'  "{cid}": {{\n'
            f'    "family": "Color Shift Overlay",\n'
            f'    "browserGroup": "Specials",\n'
            f'    "browserSection": "Color Shift Overlays",\n'
            f'    "hero": false,\n'
            f'    "featured": true,\n'
            f'    "advanced": false,\n'
            f'    "utility": false,\n'
            f'    "readability": 70,\n'
            f'    "distinctness": 70,\n'
            f'    "sortPriority": 60,\n'
            f'    "score": 70\n'
            f'  }},\n'
        )
        parts.append(block)

    # Insert before the final closing brace of FINISH_METADATA.
    closer_pat = re.compile(r'\n\};\s*\n\s*//\s*=+\s*\n\s*//\s*TIER_ASSIGNMENTS', re.MULTILINE)
    m = closer_pat.search(text)
    if not m:
        # Fallback: just before the very first `};\n` after FINISH_METADATA opens
        opener = text.find("const FINISH_METADATA")
        closer = text.find("\n};", opener)
        if closer < 0:
            return text, [], skipped_present
        new_text = text[:closer] + "".join(parts) + text[closer:]
    else:
        # Insert just before the `};` that closes FINISH_METADATA.
        # m.start() is the `\n};` sequence.
        new_text = text[:m.start()] + "".join(parts) + text[m.start():]

    return new_text, inserted, skipped_present


def _set_advanced(text, cid):
    rx = _block_re(cid)
    m = rx.search(text)
    if not m:
        return text, "missing"
    head, body, tail = m.group(1), m.group(2), m.group(3)
    new_body, _ = _replace_value(body, "advanced", True)
    if new_body == body:
        return text, "ok"
    return text[:m.start()] + head + new_body + tail + text[m.end():], "patched"


def _disambiguate_cs_names(text):
    """Update the MONOLITHICS display name in paint-booth-0-finish-data.js."""
    changed = []
    for cid, old_name, new_name, _reason in CS_NAME_FIXES:
        # Match the exact `name: "..."` on the line containing the id.
        line_pat = re.compile(
            r'(\{\s*id:\s*"' + re.escape(cid) + r'",\s*name:\s*)"' + re.escape(old_name) + r'"'
        )
        m = line_pat.search(text)
        if not m:
            continue
        replacement = f'\\1"{new_name}"'
        new_text = line_pat.sub(replacement, text)
        if new_text != text:
            text = new_text
            changed.append(cid)
    return text, changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    # Pass 1: metadata file changes (cs_* insertion + cx_* demotion).
    for path in METADATA_PATHS:
        if not path.exists():
            print(f"  SKIP missing: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        text2, inserted, skipped = _ensure_cs_metadata(text)
        demoted = []
        for cid in CX_DEMOTE_IDS:
            text2, status = _set_advanced(text2, cid)
            if status == "patched":
                demoted.append(cid)
        rel = path.relative_to(REPO)
        print(f"  {rel}:")
        print(f"    cs_* metadata inserted: {len(inserted)}  (already present: {len(skipped)})")
        print(f"    cx_* clones demoted:    {len(demoted)}")
        if not args.dry and text2 != text:
            path.write_text(text2, encoding="utf-8")

    # Pass 2: data file changes (display-name disambiguation).
    for path in DATA_PATHS:
        if not path.exists():
            print(f"  SKIP missing: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        text2, changed = _disambiguate_cs_names(text)
        rel = path.relative_to(REPO)
        print(f"  {rel}: cs_* name disambiguations: {len(changed)} ({changed})")
        if not args.dry and text2 != text:
            path.write_text(text2, encoding="utf-8")

    print("\n[DONE]" if not args.dry else "\n[DRY-RUN]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
