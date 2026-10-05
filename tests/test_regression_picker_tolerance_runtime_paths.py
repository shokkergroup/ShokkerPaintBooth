"""Regression guardrail — `pickerTolerance` runtime code paths must
not silently clobber painter-set 0.

## Context (2026-04-21 post-Codex-audit fix)

The HEENAN OVERNIGHT loop's iter 1 + iter 8 fixed `pickerTolerance`
preservation on the PERSISTENCE boundary (preset import + export).
A Codex audit found that the fix stopped there: six live painter-
facing runtime paths in `paint-booth-2-state-zones.js` still used
`zone.pickerTolerance || 40`. A preset with `pickerTolerance: 0`
loaded as 0 correctly, but the first interaction with the zone
(color add, color pick, render-coverage estimate, zone duplicate)
coerced it back to 40 before the engine ever saw the painter's
intent. The "exact-match color selector" claim was false end-to-end.

This test pins ZERO live `pickerTolerance ||` occurrences in the
zone source. If any future change reintroduces `||` on a
`pickerTolerance` read, this test fires immediately.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ZONES_JS = REPO / "paint-booth-2-state-zones.js"


def test_no_picker_tolerance_logical_or_clobber():
    """Any `pickerTolerance` read paired with `||` silently coerces a
    painter-set 0 to the default. All such reads must use `??`.

    This test catches regressions across the ENTIRE file, including:
      - color-add helpers (line ~1049)
      - zone detail UI rendering (lines ~1245, 1252)
      - picker / hex setters (lines ~3971, 4025)
      - render-coverage estimator (line ~10029)
      - duplicateZone helper (line ~11247)
    """
    src = ZONES_JS.read_text(encoding="utf-8")
    # Find any `<...>pickerTolerance<optional whitespace>||` occurrence.
    # The painter-visible class of bug is specifically `something.pickerTolerance ||`.
    bad_pattern = re.compile(r"pickerTolerance\s*\|\|")
    matches = list(bad_pattern.finditer(src))
    locations = []
    for m in matches:
        line_num = src[: m.start()].count("\n") + 1
        line_start = src.rfind("\n", 0, m.start()) + 1
        line_end = src.find("\n", m.start())
        snippet = src[line_start:line_end].strip()[:120]
        locations.append(f"  line {line_num}: {snippet}")

    assert not matches, (
        "paint-booth-2-state-zones.js contains `pickerTolerance ||` — a "
        "painter-set tolerance=0 (exact-match selector) will be silently "
        "coerced to the default. Switch to `??` (nullish coalesce).\n"
        + "\n".join(locations)
    )


def test_picker_tolerance_nullish_coalesce_still_widely_used():
    """Positive confirmation — after the post-audit fix, the file
    contains multiple `pickerTolerance ??` occurrences (persistence
    paths + runtime paths). If every occurrence vanished, something
    restructured the access patterns and this guardrail needs review.
    """
    src = ZONES_JS.read_text(encoding="utf-8")
    coalesce_pattern = re.compile(r"pickerTolerance\s*\?\?")
    count = len(coalesce_pattern.findall(src))
    assert count >= 6, (
        f"Only {count} `pickerTolerance ??` occurrences in the file. "
        f"Expected at least 6 (persistence paths from iter 1/8 + "
        f"runtime paths from post-audit). The field may have been "
        f"renamed or consolidated — verify tolerance handling still "
        f"preserves painter-set 0 everywhere."
    )
