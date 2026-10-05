"""HEENAN 5H OVERNIGHT — iter 8 behavioral proof for the
`exportPreset` falsy-value preservation fix.

Pre-fix state: `paint-booth-2-state-zones.js::exportPreset` mapped
zones to preset entries using `||` on numeric/boolean persistence
fields. A painter with `zone.scale: 0` (degenerate but legitimate)
would have `scale: 1.0` serialized into the shareable .shokker
file — recipients got the wrong setup.

Post-fix: the mapping uses `??` for scale/rotation/wear/muted/
patternOpacity (matching the `loadConfigFromObj` and
`_applyPresetFromObject` convention). Arrays (patternStack etc.)
stay on `||` because empty array ≈ missing field on this path.

This file runs `tests/_runtime_harness/export_preset_falsy.mjs`,
which extracts the live exportPreset mapping block from source,
runs it in a V8 sandbox with a zone whose every falsy-legitimate
field is falsy, and asserts all values round-trip. A negative-
control mutation proves the test infrastructure still catches
the regression it claims to guard against.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "export_preset_falsy.mjs"


def _run_harness():
    if shutil.which("node") is None:
        pytest.skip("node not on PATH; runtime harness requires Node 18+")
    assert HARNESS.exists(), f"missing: {HARNESS}"
    proc = subprocess.run(
        ["node", str(HARNESS)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode not in (0, 3):
        pytest.fail(
            f"export_preset_falsy harness crashed (exit {proc.returncode}):\n"
            f"stdout: {proc.stdout[:500]}\nstderr: {proc.stderr[:500]}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def harness():
    return _run_harness()


FIELDS_EXPECTED = [
    ("scale", 0),
    ("rotation", 0),
    ("wear", 0),
    ("muted", False),
    ("patternOpacity", 0),
]


@pytest.mark.parametrize("field,expected", FIELDS_EXPECTED)
def test_export_preset_preserves_falsy_value(harness, field, expected):
    """Each numeric/boolean persistence field must round-trip through
    the exportPreset zones.map with its falsy value intact.
    """
    checks = harness.get("fields", {})
    assert field in checks, (
        f"Harness did not report a check for {field!r}. "
        f"Fields available: {sorted(checks.keys())}"
    )
    entry = checks[field]
    assert entry["ok"], (
        f"{field}: expected {entry['expected']!r} (reason: {entry['reason']}), "
        f"got {entry['got']!r}. exportPreset is serializing the wrong value — "
        f"a painter with this setting gets a different render in recipient's "
        f"render."
    )


def test_export_preset_negative_control_catches_regression(harness):
    """The harness mutates the extracted mapping to put `||` back on
    scale, re-runs in a fresh sandbox. It must observe the regression
    (scale=0 → 1.0). This proves the test can still detect the bug
    class it guards against.
    """
    nc = harness.get("negative_control", {})
    assert nc.get("ran") is True, (
        f"Negative control did NOT run. Harness reports: {nc}. "
        f"Likely the `scale: z.scale ?? 1.0` literal moved or changed "
        f"shape — update the mutation site in "
        f"tests/_runtime_harness/export_preset_falsy.mjs."
    )
    assert nc.get("caught_regression") is True, (
        f"Negative-control mutation (swap ?? for ||) did NOT produce "
        f"the expected regression. scale passed through as "
        f"{nc.get('passed_through')!r} (expected 1.0). The harness is "
        f"not running the mutated block correctly — it's giving false "
        f"confidence."
    )
