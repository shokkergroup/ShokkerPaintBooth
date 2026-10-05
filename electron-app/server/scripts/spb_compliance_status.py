#!/usr/bin/env python3
"""
SPB doctrine + perf compliance status — one-page rollup for the entire SPB-90
+ doctrine-audit family. Reads the 5 audit JSONs that ticks 31-66 produced and
prints a clean snapshot of catalog health.

Pure read-only. Runs in < 1 second. Useful when you want a 5-line "where do
we stand?" answer without spinning up the painter or re-running 8-minute audits.

USAGE
-----
    python scripts/spb_compliance_status.py

OUTPUT
------
Compact table with:
  * Doctrine intent counts (catalog-wide)
  * Each of the 4 doctrine audits + their pass/fail count
  * The 1 registry-orphan audit
  * The latest perf-audit numbers (cold)
  * Live counts of CI regression tests

The JSON files are read straight off disk — run the individual audit scripts
first to refresh any stale numbers (see DATA_SOURCES below).

DATA SOURCES
------------
_workbook_metrics/m_paint_neutrality.json          tick 31 onward
_workbook_metrics/m_spec_richness.json             tick 32 onward
_workbook_metrics/m_pattern_design_paint.json      tick 41 onward
_workbook_metrics/m_placeholders.json              tick 37 onward
_workbook_metrics/m_pattern_image_chroma.json      tick 66 onward
_workbook_metrics/m_render_perf.json               tick 48 onward (8-min refresh)
"""
from __future__ import annotations

import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

V5_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V5_ROOT))
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

WORKBOOK_DIR = V5_ROOT / "_workbook_metrics"


def _safe_load(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _age_label(path: Path) -> str:
    if not path.exists():
        return "missing"
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    secs = (now - mtime).total_seconds()
    if secs < 60:
        return f"{int(secs)}s ago"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


def _check(passing: bool) -> str:
    return "✓" if passing else "✗"


def _read_intent_counts() -> dict[str, int]:
    """Parse scorecard categories and tally by surface_intent."""
    try:
        from engine.paint_v2.surface_intent import get_intent
    except Exception:
        return {}
    scorecard = V5_ROOT / "paint-booth-0-catalog-scorecard.js"
    if not scorecard.exists():
        return {}
    txt = scorecard.read_text(encoding="utf-8", errors="replace")
    counts: dict[str, int] = {}
    for m in re.finditer(
        r'"([a-z_]+:[a-z0-9_]+)":\s*\{[^{}]*?"category":\s*"([^"]+)"',
        txt,
        flags=re.S,
    ):
        intent = get_intent(m.group(2))
        counts[intent] = counts.get(intent, 0) + 1
    return counts


def _count_ci_tests() -> tuple[int, int]:
    """Returns (doctrine_count, perf_count) by parsing the two test files."""
    tests_dir = V5_ROOT / "tests"
    doctrine = tests_dir / "test_regression_spec_doctrine.py"
    perf = tests_dir / "test_regression_render_perf.py"
    doc_count = 0
    if doctrine.exists():
        doc_count = doctrine.read_text(encoding="utf-8").count("\ndef test_")
    perf_count = 0
    if perf.exists():
        # parametrize tuples → one test each
        txt = perf.read_text(encoding="utf-8")
        # Count tuples in PERF_REPRESENTATIVES
        m = re.search(r"PERF_REPRESENTATIVES\s*=\s*\[(.+?)^\]", txt, flags=re.S | re.M)
        if m:
            perf_count = len(re.findall(r"^\s*\(\"(?:mono|base)\"", m.group(1), flags=re.M))
    return doc_count, perf_count


def main() -> int:
    print("=" * 72)
    print("SPB Compliance Status — read-only rollup of all audit JSONs")
    print("=" * 72)

    # Doctrine intent counts
    print()
    print("Doctrine intent distribution (catalog-wide):")
    intents = _read_intent_counts()
    if intents:
        total = sum(intents.values())
        for intent in ("spec_driven", "pattern_design", "pattern_image", "full"):
            n = intents.get(intent, 0)
            pct = (n / total * 100) if total else 0
            print(f"  {intent:18s}  {n:>5}  ({pct:.1f}%)")
        print(f"  {'TOTAL':18s}  {total:>5}")
    else:
        print("  (scorecard or surface_intent.py unavailable)")

    print()
    print("Doctrine compliance audits (5):")
    print(f"  {'audit':<32s}  {'pass':>6s}  {'total':>6s}  {'age':<10s}  {'status':<6s}")

    # Paint-neutrality (spec_driven)
    p = WORKBOOK_DIR / "m_paint_neutrality.json"
    data = _safe_load(p)
    if data:
        passing = data.get("n_clean", 0)
        total = data.get("n_probed", 0)
        ok = data.get("n_suspect", 0) == 0
        print(f"  {'paint-neutrality (spec_driven)':<32s}  {passing:>6}  {total:>6}  {_age_label(p):<10s}  {_check(ok):<6s}")
    else:
        print(f"  paint-neutrality: missing")

    # Spec-richness
    p = WORKBOOK_DIR / "m_spec_richness.json"
    data = _safe_load(p)
    if data:
        rich = data.get("n_rich", 0)
        total = data.get("n_probed", 0)
        print(f"  {'spec-richness (spec_driven)':<32s}  {rich:>6}  {total:>6}  {_age_label(p):<10s}  {_check(False):<6s} (known limitation — high-freq content washes in 32-block averaging)")
    else:
        print(f"  spec-richness: missing")

    # Pattern_design paint richness
    p = WORKBOOK_DIR / "m_pattern_design_paint.json"
    data = _safe_load(p)
    if data:
        rich = data.get("n_rich", 0)
        total = data.get("n_probed", 0)
        ok = data.get("n_quiet", 0) == 0
        print(f"  {'pattern_design paint richness':<32s}  {rich:>6}  {total:>6}  {_age_label(p):<10s}  {_check(ok):<6s}")
    else:
        print(f"  pattern_design paint: missing")

    # Pattern_image chroma
    p = WORKBOOK_DIR / "m_pattern_image_chroma.json"
    data = _safe_load(p)
    if data:
        genuine = data.get("n_genuine_pattern_image", 0)
        total = data.get("n_total", 0)
        miscat = data.get("n_likely_pattern_design", 0)
        ok = miscat == 0
        print(f"  {'pattern_image chroma':<32s}  {genuine:>6}  {total:>6}  {_age_label(p):<10s}  {_check(ok):<6s} ({miscat} miscategorized — SPB-94 pending)")
    else:
        print(f"  pattern_image: missing")

    # Placeholders (registry orphan)
    p = WORKBOOK_DIR / "m_placeholders.json"
    data = _safe_load(p)
    if data:
        b = data.get("base_registry", {})
        m = data.get("monolithic_registry", {})
        orphans = len(b.get("placeholder_ids", [])) + len(m.get("placeholder_ids", []))
        wired = b.get("fully_wired", 0) + m.get("fully_wired", 0)
        total = b.get("total", 0) + m.get("total", 0)
        ok = orphans == 0
        print(f"  {'registry placeholder orphans':<32s}  {wired:>6}  {total:>6}  {_age_label(p):<10s}  {_check(ok):<6s} ({orphans} orphan{'s' if orphans != 1 else ''})")
    else:
        print(f"  registry placeholders: missing")

    # Perf audit
    print()
    print("Render perf audit (last run):")
    p = WORKBOOK_DIR / "m_render_perf.json"
    data = _safe_load(p)
    if data:
        clean = data.get("n_ok", 0)
        total = data.get("n_probed", 0)
        over = data.get("n_over_threshold", 0)
        print(f"  finishes probed: {total}  clean: {clean}  over {data.get('threshold_ms', 50)}ms threshold: {over}")
        print(f"  audit data age:  {_age_label(p)}")
    else:
        print(f"  m_render_perf.json missing — run scripts/audit_render_perf.py")

    # CI regression tests
    print()
    doc_count, perf_count = _count_ci_tests()
    print(f"CI regression tests defined: {doc_count + perf_count} total ({doc_count} doctrine + {perf_count} perf)")
    print(f"  (run: python -m pytest tests/test_regression_spec_doctrine.py tests/test_regression_render_perf.py)")

    print()
    print("Refresh individual audits (under 5s each):")
    print("  python scripts/audit_spec_driven_paint_neutrality.py --json _workbook_metrics/m_paint_neutrality.json")
    print("  python scripts/audit_spec_driven_spec_richness.py    --json _workbook_metrics/m_spec_richness.json")
    print("  python scripts/audit_pattern_design_paint_richness.py --json _workbook_metrics/m_pattern_design_paint.json")
    print("  python scripts/audit_registry_placeholders.py        --json _workbook_metrics/m_placeholders.json")
    print("  python scripts/audit_pattern_image_chroma.py         --json _workbook_metrics/m_pattern_image_chroma.json")
    print("  python scripts/audit_render_perf.py                  --json _workbook_metrics/m_render_perf.json  # 8 min full catalog")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
