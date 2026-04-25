"""HEENAN HARDMODE-DISCO-3..5 — hero metadata + search keyword honesty.

Three discoverability fixes from the Pillman audit:

(3) `piano_black` and `wet_look` are flagship show-car finishes (Audi/BMW
    piano lacquer, fresh-waxed concours) but ship at sortPriority=50,
    featured=false, browserGroup="Full Library" — buried beneath dozens
    of niche specialty entries. They are now in HERO_BASES (HARDMODE-DISCO-1
    in paint-booth-0-finish-data.js); also bump their metadata so
    Materials/Specials searches surface them up top.

(4) `carbon_base` is OK in metadata (hero=true, sortPriority=100) but its
    browserSection of "Carbon & Composite" works — no metadata change
    needed. HERO_BASES inclusion is the win.

(5) SEARCH_KEYWORDS index is missing common painter search terms. Add
    "satin" and "wet" buckets so painters who type those words actually
    find the matching finishes.

Idempotent — re-runs produce no changes once normalized.
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


# (id, target updates dict)
HERO_PROMOTIONS = [
    ("piano_black", {
        "family": "Foundation",
        "browserGroup": "Materials",
        "browserSection": "Foundation",
        "featured": True,
        "sortPriority": 95,
    }),
    ("wet_look", {
        "family": "Foundation",
        "browserGroup": "Materials",
        "browserSection": "Foundation",
        "featured": True,
        "sortPriority": 95,
    }),
]

# New SEARCH_KEYWORDS buckets to insert.
SEARCH_KEYWORD_INSERTS = [
    ("satin", [
        "satin", "satin_chrome", "satin_gold", "satin_metal", "satin_wrap",
        "enh_satin", "enh_satin_chrome", "enh_clear_satin", "f_clear_satin",
        "gunmetal_satin", "scuffed_satin", "satin_candy",
    ]),
    ("wet", [
        "wet_look", "enh_wet_look", "liquid_wrap", "diamond_coat",
        "ceramic", "showroom_clear", "race_day_gloss", "gel_coat",
    ]),
    ("piano", [
        "piano_black", "enh_piano_black", "obsidian", "vantablack",
        "f_pure_black", "enh_pure_black",
    ]),
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


def _promote_hero(text, entry_id, updates):
    rx = _block_re(entry_id)
    m = rx.search(text)
    if not m:
        return text, "missing"
    head, body, tail = m.group(1), m.group(2), m.group(3)
    new_body = body
    changed = False
    for k, v in updates.items():
        new_body2, _ = _replace_value(new_body, k, v)
        if new_body2 != new_body:
            new_body = new_body2
            changed = True
    if not changed:
        return text, "ok"
    return text[:m.start()] + head + new_body + tail + text[m.end():], "patched"


def _ensure_search_keywords(text):
    """Insert new keyword buckets just before the closing brace of
    SEARCH_KEYWORDS, guaranteeing a trailing comma on the PREVIOUS entry
    so the resulting JS still parses.

    2026-04-20 HEENAN HARDMODE-FIX-COMMA — the first version of this
    helper inserted new entries without checking whether the prior entry
    already ended with a comma. If the prior entry was terminated with
    `]\\n` (no trailing comma — legal JS because it was the last element)
    the new insertion appended a sibling block after `]` with no comma,
    producing `]\\n  "new": [...]` which is a parse error. Rebuild the
    insertion so we always emit a leading comma-newline if the previous
    line needs one.
    """
    inserted = []
    for kw, ids in SEARCH_KEYWORD_INSERTS:
        if re.search(r'\s+"' + re.escape(kw) + r'"\s*:\s*\[', text):
            continue
        block = '  "' + kw + '": [' + ', '.join('"' + i + '"' for i in ids) + '],'
        opener = text.find("const SEARCH_KEYWORDS")
        if opener < 0:
            return text, []
        closer = text.find("\n};", opener)
        if closer < 0:
            return text, []
        # Check whether the last non-blank character before the closing
        # `};` is a comma. If not, it means the previous entry ends with
        # a bare `]` and we must add a comma to it before inserting.
        prefix = text[opener:closer]
        last_non_ws = prefix.rstrip()
        needs_comma = not last_non_ws.endswith(",")
        if needs_comma:
            # Find the end of the last character and inject a comma.
            # `prefix` ends at the rstripped text; compute absolute
            # position and splice the comma in.
            trailing_ws_len = len(prefix) - len(last_non_ws)
            last_char_abs = opener + len(prefix) - trailing_ws_len
            text = text[:last_char_abs] + "," + text[last_char_abs:]
            # Reposition closer (it moved by +1 because we added a char).
            closer += 1
        text = text[:closer] + "\n" + block + text[closer:]
        inserted.append(kw)
    return text, inserted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    grand_promoted = 0
    grand_kw = 0
    for path in METADATA_PATHS:
        if not path.exists():
            print(f"  SKIP missing: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        promoted = []
        for eid, updates in HERO_PROMOTIONS:
            text, status = _promote_hero(text, eid, updates)
            if status == "patched":
                promoted.append(eid)
        text, inserted_kw = _ensure_search_keywords(text)
        rel = path.relative_to(REPO)
        print(f"  {rel}:")
        print(f"    hero promotions: {len(promoted)} {promoted}")
        print(f"    search keywords inserted: {len(inserted_kw)} {inserted_kw}")
        grand_promoted += len(promoted)
        grand_kw += len(inserted_kw)
        if not args.dry and (promoted or inserted_kw):
            path.write_text(text, encoding="utf-8")

    print(f"\n[{'DRY-RUN' if args.dry else 'APPLIED'}] hero promotions: {grand_promoted}, kw inserts: {grand_kw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
