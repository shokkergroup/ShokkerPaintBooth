"""HEENAN HSIG-FOUND-2 — ★ Enhanced Foundation metadata normalization.

The 30 entries in BASE_GROUPS["★ Enhanced Foundation"] are marketed with a
star ("★ Enhanced ...") but their metadata is wildly inconsistent:

  enh_metallic    → browserGroup=Materials,    featured=true,  sortPriority=80
  enh_chrome      → browserGroup=Full Library, featured=true,  sortPriority=80
  enh_pearl       → browserGroup=Specials,     featured=false, sortPriority=50
  enh_gloss       → browserGroup=Utility,      featured=false, sortPriority=50, utility=true
  enh_satin       → browserGroup=Utility,      featured=false, sortPriority=50, utility=true

Painter sees the ★ tile, expects premium treatment, and gets utility-tier
sort behavior (low priority, no featured badge, hidden under "Utility").
That is a trust violation — the picker disagrees with the marketing.

This harness rewrites every enh_* entry to consistent premium metadata:
  browserGroup   = "Materials"   (so Materials tab surfaces them)
  browserSection = "★ Enhanced Foundation"
  featured       = True
  utility        = False
  hero           = False         (HERO_BASES is the curated quick-start lane)
  sortPriority   = 90            (above plain Foundation entries at 80)

Idempotent — re-running produces no changes once normalized.

Run:  python tests/_runtime_harness/normalize_enhanced_foundation_metadata.py [--dry]
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

CANONICAL_PATHS = [
    REPO / "paint-booth-0-finish-metadata.js",
    REPO / "electron-app" / "server" / "paint-booth-0-finish-metadata.js",
    REPO / "electron-app" / "server" / "pyserver" / "_internal" / "paint-booth-0-finish-metadata.js",
]

# Source of truth: the 30 ids in BASE_GROUPS["★ Enhanced Foundation"].
ENH_IDS = [
    "enh_gloss", "enh_matte", "enh_satin", "enh_metallic", "enh_pearl",
    "enh_chrome", "enh_satin_chrome", "enh_anodized", "enh_baked_enamel",
    "enh_brushed", "enh_carbon_fiber", "enh_frozen", "enh_gel_coat",
    "enh_powder_coat", "enh_vinyl_wrap", "enh_soft_gloss", "enh_soft_matte",
    "enh_warm_white", "enh_ceramic_glaze", "enh_silk", "enh_eggshell",
    "enh_primer", "enh_clear_matte", "enh_semi_gloss", "enh_wet_look",
    "enh_piano_black", "enh_living_matte", "enh_neutral_grey",
    "enh_clear_satin", "enh_pure_black",
]


def _block_re(entry_id):
    """Match `  "id": { ... },` block (multi-line, balanced braces)."""
    return re.compile(
        r'(  "' + re.escape(entry_id) + r'":\s*\{)([^}]*)(\})',
        re.MULTILINE | re.DOTALL,
    )


def _patch_block(body, key, new_value):
    """Replace `"key": <old>` with `"key": <new>` inside an entry body."""
    if isinstance(new_value, bool):
        v = "true" if new_value else "false"
    elif isinstance(new_value, str):
        v = json.dumps(new_value)
    else:
        v = str(new_value)
    pat = re.compile(r'"' + re.escape(key) + r'":\s*("[^"]*"|true|false|-?\d+)')
    if pat.search(body):
        # Use lambda to avoid backslash-template interpretation (e.g. \u escapes).
        replacement = f'"{key}": {v}'
        return pat.sub(lambda _m, _r=replacement: _r, body), True
    # Key absent — append before closing
    body = body.rstrip()
    if body.endswith(","):
        body = body[:-1]
    body += f',\n    "{key}": {v}\n  '
    return body, True


def _normalize_entry(text, entry_id):
    rx = _block_re(entry_id)
    m = rx.search(text)
    if not m:
        return text, False, "missing"
    head, body, tail = m.group(1), m.group(2), m.group(3)
    new_body = body
    changed = False
    for key, new_val in [
        ("browserGroup", "Materials"),
        ("browserSection", "\u2605 Enhanced Foundation"),
        ("featured", True),
        ("utility", False),
        ("sortPriority", 90),
        ("advanced", False),
    ]:
        new_body2, _ = _patch_block(new_body, key, new_val)
        if new_body2 != new_body:
            changed = True
            new_body = new_body2
    if not changed:
        return text, False, "ok"
    return text[:m.start()] + head + new_body + tail + text[m.end():], True, "patched"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    grand_changed = 0
    grand_missing = 0

    for path in CANONICAL_PATHS:
        if not path.exists():
            print(f"  SKIP missing: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        per_file_changed = 0
        per_file_missing = 0
        for eid in ENH_IDS:
            text2, did_change, status = _normalize_entry(text, eid)
            if status == "missing":
                per_file_missing += 1
                continue
            if did_change:
                text = text2
                per_file_changed += 1
        rel = path.relative_to(REPO)
        print(f"  {rel}: {per_file_changed} normalized, {per_file_missing} missing")
        grand_changed += per_file_changed
        grand_missing += per_file_missing
        if not args.dry and per_file_changed > 0:
            path.write_text(text, encoding="utf-8")

    mode = "[DRY-RUN]" if args.dry else "[APPLIED]"
    print(f"\n{mode} Total normalized: {grand_changed}, total missing: {grand_missing}")
    return 1 if grand_missing > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
