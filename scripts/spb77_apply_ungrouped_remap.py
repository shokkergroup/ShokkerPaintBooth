#!/usr/bin/env python3
"""
SPB-77 — apply the 'Ungrouped Base' → real-category remap.

Owner-gated tick-68 proposal. Run once when SPB-77 lands. Mechanical edit
of `paint-booth-0-catalog-scorecard.js` to remap the 113 finishes currently
in `category: "Ungrouped Base"` to their real homes via name-prefix.

USAGE
-----
    # Default: dry run — show what would change, no writes
    python scripts/spb77_apply_ungrouped_remap.py

    # Apply (writes scorecard JS atomically via temp + rename)
    python scripts/spb77_apply_ungrouped_remap.py --apply

POST-APPLY
----------
After --apply:
1. Re-run `python scripts/audit_render_perf.py --json _workbook_metrics/m_render_perf.json`
   The 'Ungrouped Base' category disappears from the rollup.
2. Re-run `python scripts/spb_compliance_status.py` to confirm intent
   distribution updates.
3. Optionally update `engine/paint_v2/surface_intent.py` with the 2 new
   categories (Anime, Neon). Default is `full` intent for both, owner picks.

REVERSAL
--------
Atomic write means the .tmp file is removed on success. To revert, restore
the scorecard from version control.
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

V5_ROOT = Path(__file__).resolve().parent.parent
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

SCORECARD = V5_ROOT / "paint-booth-0-catalog-scorecard.js"

# Tick-68 mapping verified against engine boot log + renderer modules.
# Total: 26 + 25 + 25 + 13 + 4 + 10 + 10 = 113.
PREFIX_TO_CATEGORY = {
    "ms":     "Mortal Shokk V2",
    "cx":     "★ COLORSHOXX",          # existing category (matches scorecard star)
    "shokk":  "SHOKK Series",
    "p":      "PARADIGM",              # existing category
    "anime":  "Anime / Stylized",      # new category
    "neon":   "Neon",                  # new category
}

# Singleton finishes that map directly (don't fit any prefix cluster).
# Match by exact stem because the prefix is ambiguous with other categories
# (e.g. `arctic` alone vs `arctic_ice` which is a PARADIGM exotic).
SINGLETON_TO_CATEGORY = {
    "arctic":          "PARADIGM",
    "arctic_ice":      "PARADIGM",
    "infinite":        "PARADIGM",
    "infinite_finish": "PARADIGM",
    "nebula":          "PARADIGM",
    "quantum":         "PARADIGM",
    "quantum_foam":    "PARADIGM",
}


def detect_category(stem: str) -> str | None:
    """Return the proposed real category, or None if no mapping applies."""
    if stem in SINGLETON_TO_CATEGORY:
        return SINGLETON_TO_CATEGORY[stem]
    prefix = stem.split("_")[0] if "_" in stem else stem
    return PREFIX_TO_CATEGORY.get(prefix)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--apply", action="store_true",
                    help="Actually write the scorecard. Default is dry run.")
    args = ap.parse_args()

    if not SCORECARD.exists():
        print(f"[spb77-remap] scorecard not found: {SCORECARD}", file=sys.stderr)
        return 1

    text = SCORECARD.read_text(encoding="utf-8")

    # Pattern: match each entry block and pull its (fid, category). We'll
    # then replace each `category: "Ungrouped Base"` line on a per-fid basis.
    entry_pat = re.compile(
        r'"([a-z_]+:[a-z0-9_]+)":\s*\{[^{}]*?"category":\s*"([^"]+)"',
        flags=re.S,
    )

    changes: list[tuple[str, str, str]] = []  # (fid, old_cat, new_cat)
    unmatched: list[str] = []
    for m in entry_pat.finditer(text):
        fid = m.group(1)
        cat = m.group(2)
        if cat != "Ungrouped Base":
            continue
        _, _, stem = fid.partition(":")
        new_cat = detect_category(stem)
        if new_cat is None:
            unmatched.append(fid)
            continue
        changes.append((fid, cat, new_cat))

    print(f"[spb77-remap] dry-run findings:")
    print(f"  total 'Ungrouped Base' entries: {len(changes) + len(unmatched)}")
    print(f"  mappable to real category:      {len(changes)}")
    print(f"  unmatched (no rule applies):    {len(unmatched)}")
    if unmatched:
        print(f"  unmatched IDs: {unmatched[:20]}")
        if len(unmatched) > 20:
            print(f"    ... and {len(unmatched) - 20} more")
    print()

    # Per-target rollup
    from collections import Counter
    cnt = Counter(new for _, _, new in changes)
    print(f"  by target category:")
    for cat, n in sorted(cnt.items(), key=lambda kv: -kv[1]):
        print(f"    {n:>4}  → {cat}")
    print()

    if not args.apply:
        print("[spb77-remap] DRY RUN — no files written. Re-run with --apply to commit.")
        return 0

    # Apply edits. For each fid in `changes`, rewrite the `category: "Ungrouped Base"`
    # to the new category. We rewrite within each entry's regex match span to
    # avoid replacing the wrong one if names collide.
    new_text = text
    for fid, _, new_cat in changes:
        # Locate the entry block by fid and replace its category line.
        # Find: `"fid": {...,"category": "Ungrouped Base",...}`
        pat = re.compile(
            r'(?P<key>"' + re.escape(fid) + r'":\s*\{[^{}]*?"category":\s*)"Ungrouped Base"',
            flags=re.S,
        )
        new_text, n = pat.subn(rf'\g<key>"{new_cat}"', new_text, count=1)
        if n == 0:
            print(f"[spb77-remap] WARN: could not rewrite {fid} (regex miss)")

    tmp_path = SCORECARD.with_suffix(".js.tmp")
    tmp_path.write_text(new_text, encoding="utf-8", newline="\n")
    import os
    os.replace(tmp_path, SCORECARD)
    print(f"[spb77-remap] APPLIED. Wrote {SCORECARD}")
    print(f"[spb77-remap] {len(changes)} entries recategorized.")
    print()
    print("NEXT:")
    print("  python scripts/audit_render_perf.py --json _workbook_metrics/m_render_perf.json")
    print("  python scripts/spb_compliance_status.py")
    print("Optional (owner picks intent for new categories):")
    print("  edit engine/paint_v2/surface_intent.py to map 'Anime / Stylized' and 'Neon' → full")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
