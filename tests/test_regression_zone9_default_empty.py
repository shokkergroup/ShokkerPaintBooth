"""Regression guardrail — Zone 9 must stay empty by default.

Painter report (2026-04-22): Zone 9 was silently seeded as a dark/carbon zone
with `matte + carbon_fiber`, which made the app feel like it was inventing a
material choice before the painter asked for one. The only default catch-all
should be Zone 10 (`Everything Else` with gloss + Remaining).
"""

from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
STATE_ZONES_JS = REPO / "paint-booth-2-state-zones.js"

ZONE9_LITERAL = (
    'name: "Open Zone 9", color: null, base: null, pattern: "none", '
    'finish: null, intensity: "80", colorMode: "none", pickerColor: "#777777", '
    'pickerTolerance: 40, colors: [], regionMask: null,'
)

ZONE10_LITERAL = (
    'name: "Everything Else", color: "remaining", base: "gloss", pattern: "none", '
    'finish: null, intensity: "50", colorMode: "special", pickerColor: "#888888", '
    'pickerTolerance: 40, colors: [], regionMask: null,'
)


def test_zone9_default_is_empty_in_both_default_paths():
    src = STATE_ZONES_JS.read_text(encoding="utf-8")

    assert src.count(ZONE9_LITERAL) == 2, (
        "Zone 9 default drifted. The live init() and restoreAllZones() paths "
        "must both keep Zone 9 empty by default."
    )
    assert src.count(ZONE10_LITERAL) == 2, (
        "Zone 10 default drifted. The Remaining/gloss safety-net zone should "
        "still exist in both init() and restoreAllZones()."
    )
    assert 'name: "Dark / Carbon Areas"' not in src, (
        "The old hardcoded Dark / Carbon default still exists in "
        "paint-booth-2-state-zones.js."
    )
