#!/usr/bin/env python3
"""
SPB-94 option A — remap 'Artistic & Cultural' category from PATTERN_IMAGE
to PATTERN_DESIGN, and add a single per-fid override for tribal_celtic_spiral
which the tick-66 audit confirmed actually carries its own color.

Owner picks A/B/C in SPB-94. This script implements option A (recommended).
Run in dry-run mode by default; pass --apply to commit.

What it changes
---------------
Edits `engine/paint_v2/surface_intent.py` (and the 2 mirror copies). Two
concrete modifications:

1. Move "Artistic & Cultural" out of the PATTERN_IMAGE block and into the
   PATTERN_DESIGN block.
2. Add a `FID_INTENT_OVERRIDE` dict near `CATEGORY_INTENT` mapping
   "pattern:tribal_celtic_spiral" → PATTERN_IMAGE.
3. Update `get_intent` to accept an optional `fid` argument and check the
   override first.

Audit script (`scripts/audit_pattern_image_chroma.py`) will need an update
in a follow-up tick — it currently walks by category. After this remap, the
pattern_image bucket becomes [tribal_celtic_spiral] only, which is the
genuinely-correct state.

USAGE
-----
    python scripts/spb94_apply_pattern_image_remap.py            # dry run
    python scripts/spb94_apply_pattern_image_remap.py --apply    # commit

REVERSAL
--------
3 files under git; revert via git if needed. Atomic via temp + rename.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

V5_ROOT = Path(__file__).resolve().parent.parent
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

# 3-copy mirror locations
TARGETS = [
    V5_ROOT / "engine" / "paint_v2" / "surface_intent.py",
    V5_ROOT / "electron-app" / "server" / "engine" / "paint_v2" / "surface_intent.py",
    V5_ROOT / "electron-app" / "server" / "pyserver" / "_internal" / "engine" / "paint_v2" / "surface_intent.py",
]

OLD_PI_BLOCK = '''    # --- PATTERN_IMAGE: image-based patterns that DO carry color ---
    # Owner has the canonical list — for now, the obvious cultural family.
    # Update as ground truth is captured.
    "Artistic & Cultural":     PATTERN_IMAGE,
    "Cultural":                PATTERN_IMAGE,'''

NEW_PI_BLOCK = '''    # --- PATTERN_IMAGE: image-based patterns that DO carry color ---
    # SPB-94 tick 72: removed "Artistic & Cultural" — only 1 of 17 finishes
    # (tribal_celtic_spiral) actually carries its own color. The rest are
    # pattern_design pass-through. Single exception lives in FID_INTENT_OVERRIDE.
    "Cultural":                PATTERN_IMAGE,'''

# Add "Artistic & Cultural" to the PATTERN_DESIGN block, immediately after Ornamental
OLD_PD_TAIL = '    "Ornamental":              PATTERN_DESIGN,\n'
NEW_PD_TAIL = '    "Ornamental":              PATTERN_DESIGN,\n    "Artistic & Cultural":     PATTERN_DESIGN,  # SPB-94 tick 72: was pattern_image\n'

# Insert FID_INTENT_OVERRIDE right after CATEGORY_INTENT dict definition
OLD_AFTER_CAT = '''    # All other categories default to `full` via DEFAULT_INTENT.
}


DEFAULT_INTENT: str = FULL'''

NEW_AFTER_CAT = '''    # All other categories default to `full` via DEFAULT_INTENT.
}


# SPB-94 tick 72: per-finish overrides for cases where the category-level
# intent is wrong for a specific finish. Keyed by "<surface>:<id>". Use
# sparingly — the category mapping is the doctrine source of truth.
FID_INTENT_OVERRIDE: dict[str, str] = {
    # tribal_celtic_spiral: only "Artistic & Cultural" finish that carries
    # its own color (chroma audit tick 66: cosine 0.66 vs 1.0000 for all
    # other entries in that category). Genuinely pattern_image.
    "pattern:tribal_celtic_spiral": PATTERN_IMAGE,
}


DEFAULT_INTENT: str = FULL'''

# Update get_intent to accept optional fid and consult the override.
OLD_GET_INTENT = '''def get_intent(category: Optional[str]) -> str:
    """Return the surface intent for a category. Falls back to ``full``."""
    if not category:
        return DEFAULT_INTENT
    return CATEGORY_INTENT.get(category, DEFAULT_INTENT)'''

NEW_GET_INTENT = '''def get_intent(category: Optional[str], fid: Optional[str] = None) -> str:
    """Return the surface intent for a category. Falls back to ``full``.

    SPB-94 tick 72: when ``fid`` is provided, check ``FID_INTENT_OVERRIDE``
    first so per-finish exceptions trump the category mapping. Existing
    callers that pass only ``category`` continue to work unchanged.
    """
    if fid and fid in FID_INTENT_OVERRIDE:
        return FID_INTENT_OVERRIDE[fid]
    if not category:
        return DEFAULT_INTENT
    return CATEGORY_INTENT.get(category, DEFAULT_INTENT)'''


def apply_to(text: str) -> tuple[str, list[str]]:
    """Returns (new_text, applied_changes). Raises if a section can't be found."""
    changes = []
    if OLD_PI_BLOCK not in text:
        return text, ["FAIL: PATTERN_IMAGE block not found"]
    text = text.replace(OLD_PI_BLOCK, NEW_PI_BLOCK)
    changes.append("removed 'Artistic & Cultural' from PATTERN_IMAGE")

    if OLD_PD_TAIL not in text:
        return text, changes + ["FAIL: PATTERN_DESIGN tail (Ornamental line) not found"]
    text = text.replace(OLD_PD_TAIL, NEW_PD_TAIL)
    changes.append("added 'Artistic & Cultural' to PATTERN_DESIGN")

    if OLD_AFTER_CAT not in text:
        return text, changes + ["FAIL: DEFAULT_INTENT block not found"]
    text = text.replace(OLD_AFTER_CAT, NEW_AFTER_CAT)
    changes.append("inserted FID_INTENT_OVERRIDE dict with tribal_celtic_spiral")

    if OLD_GET_INTENT not in text:
        return text, changes + ["FAIL: get_intent body not found"]
    text = text.replace(OLD_GET_INTENT, NEW_GET_INTENT)
    changes.append("extended get_intent() with optional fid + override lookup")
    return text, changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--apply", action="store_true", help="Commit the edits.")
    args = ap.parse_args()

    print(f"[spb94-remap] surface_intent.py 3-copy mirror remap")
    print(f"  mode: {'APPLY' if args.apply else 'dry-run'}")
    print()

    all_ok = True
    for path in TARGETS:
        if not path.exists():
            print(f"  MISSING: {path}")
            all_ok = False
            continue
        text = path.read_text(encoding="utf-8")
        new_text, changes = apply_to(text)
        applied = sum(1 for c in changes if not c.startswith("FAIL"))
        failed = [c for c in changes if c.startswith("FAIL")]
        print(f"  {path.relative_to(V5_ROOT)}")
        for c in changes:
            marker = "✓" if not c.startswith("FAIL") else "✗"
            print(f"    {marker} {c}")
        if failed:
            all_ok = False
            continue
        if args.apply:
            tmp = path.with_suffix(".py.tmp")
            tmp.write_text(new_text, encoding="utf-8", newline="\n")
            os.replace(tmp, path)
            print(f"    WROTE {path.name}")
        else:
            # Sanity: confirm the new text differs
            if new_text == text:
                print(f"    (no diff — already applied?)")

    print()
    if not all_ok:
        print("[spb94-remap] one or more files failed to patch. Aborted.")
        return 1
    if args.apply:
        print("[spb94-remap] DONE. NEXT:")
        print("  python -m pytest tests/test_regression_spec_doctrine.py tests/test_owner_rating_io.py tests/test_regression_render_perf.py")
        print("  python scripts/audit_pattern_image_chroma.py --json _workbook_metrics/m_pattern_image_chroma.json")
        print("  python scripts/spb_compliance_status.py")
        print()
        print("Follow-up tick: update audit_pattern_image_chroma.py to walk fids and")
        print("respect FID_INTENT_OVERRIDE. Currently it walks categories so the")
        print("audit will report 0 candidates post-apply until that update lands.")
    else:
        print("[spb94-remap] DRY RUN — no files written. Re-run with --apply to commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
