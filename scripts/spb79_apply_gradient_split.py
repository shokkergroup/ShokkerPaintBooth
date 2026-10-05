#!/usr/bin/env python3
"""
SPB-79 — split the 91-entry "Gradient Extended" category by suffix.

Owner-gated tick-75 proposal. Default is the 2-way split (recommended):
  *_vortex (40 finishes)  → 'Gradient Vortex' (new)
  everything else (51)    → stays 'Gradient Extended' (residual scope)

Pass --three-way for the alternate split:
  *_vortex (40)           → 'Gradient Vortex'
  *_gold (6)              → 'Gradient Color Pairs'
  *_h / *_diag (9)        → 'Gradient Directional'
  everything else (36)    → stays 'Gradient Extended'

USAGE
-----
    # Default: dry run, 2-way split
    python scripts/spb79_apply_gradient_split.py

    # Apply 2-way (recommended)
    python scripts/spb79_apply_gradient_split.py --apply

    # Apply 3-way
    python scripts/spb79_apply_gradient_split.py --three-way --apply

POST-APPLY
----------
1. Re-run perf audit so per-category rollups reflect the split:
   python scripts/audit_render_perf.py --json _workbook_metrics/m_render_perf.json
2. Optional: add intent mappings for the new categories in surface_intent.py
   (likely PATTERN_DESIGN since gradients are about pattern not paint color).
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
from collections import Counter
from pathlib import Path

V5_ROOT = Path(__file__).resolve().parent.parent
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

SCORECARD = V5_ROOT / "paint-booth-0-catalog-scorecard.js"


def detect_target(stem: str, three_way: bool) -> str:
    """Return the new category for this finish, or 'Gradient Extended' for residual."""
    parts = stem.split("_")
    last = parts[-1] if parts else stem
    if last == "vortex":
        return "Gradient Vortex"
    if not three_way:
        # 2-way: everything else stays in 'Gradient Extended'
        return "Gradient Extended"
    # 3-way: classify further
    if last == "gold":
        return "Gradient Color Pairs"
    if last in ("h", "diag"):
        return "Gradient Directional"
    return "Gradient Extended"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--apply", action="store_true", help="Commit (default is dry run).")
    ap.add_argument("--three-way", action="store_true",
                    help="Use the 3-way split (vortex + color-pairs + directional + residual). "
                         "Default is 2-way (vortex + residual).")
    args = ap.parse_args()

    if not SCORECARD.exists():
        print(f"[spb79-split] scorecard not found: {SCORECARD}", file=sys.stderr)
        return 1

    text = SCORECARD.read_text(encoding="utf-8")
    entry_pat = re.compile(
        r'"([a-z_]+:[a-z0-9_]+)":\s*\{[^{}]*?"category":\s*"([^"]+)"',
        flags=re.S,
    )

    changes: list[tuple[str, str]] = []  # (fid, new_cat) — old_cat is always "Gradient Extended"
    for m in entry_pat.finditer(text):
        fid = m.group(1)
        cat = m.group(2)
        if cat != "Gradient Extended":
            continue
        _, _, stem = fid.partition(":")
        target = detect_target(stem, args.three_way)
        if target != "Gradient Extended":  # only count actual reassignments
            changes.append((fid, target))

    mode = "3-way" if args.three_way else "2-way"
    print(f"[spb79-split] dry-run findings ({mode} split):")
    total = sum(1 for m in entry_pat.finditer(text) if m.group(2) == "Gradient Extended")
    print(f"  total 'Gradient Extended' entries: {total}")
    print(f"  moved to a new category:           {len(changes)}")
    print(f"  staying in 'Gradient Extended':    {total - len(changes)}")
    print()
    cnt = Counter(new for _, new in changes)
    print("  by target category:")
    for cat, n in sorted(cnt.items(), key=lambda kv: -kv[1]):
        print(f"    {n:>4}  → {cat}")
    if total - len(changes) > 0:
        print(f"    {total - len(changes):>4}  → Gradient Extended (residual)")
    print()

    if not args.apply:
        print("[spb79-split] DRY RUN — no files written. Re-run with --apply to commit.")
        return 0

    new_text = text
    for fid, new_cat in changes:
        pat = re.compile(
            r'(?P<key>"' + re.escape(fid) + r'":\s*\{[^{}]*?"category":\s*)"Gradient Extended"',
            flags=re.S,
        )
        new_text, n = pat.subn(rf'\g<key>"{new_cat}"', new_text, count=1)
        if n == 0:
            print(f"[spb79-split] WARN: could not rewrite {fid}")

    tmp_path = SCORECARD.with_suffix(".js.tmp")
    tmp_path.write_text(new_text, encoding="utf-8", newline="\n")
    os.replace(tmp_path, SCORECARD)
    print(f"[spb79-split] APPLIED. {len(changes)} entries recategorized.")
    print()
    print("NEXT:")
    print("  python scripts/audit_render_perf.py --json _workbook_metrics/m_render_perf.json")
    print("  python scripts/spb_compliance_status.py")
    print("Optional: edit engine/paint_v2/surface_intent.py to give the new categories an intent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
