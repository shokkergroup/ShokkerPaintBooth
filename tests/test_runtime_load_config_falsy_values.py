"""HEENAN 5H OVERNIGHT — iter 4 behavioral upgrade for loadConfigFromObj.

Before this file: `tests/test_regression_save_load_repair_integrity.py`
had 19 parametric source-text assertions checking that
`loadConfigFromObj` writes `field: z.field ?? default` (not `|| default`)
for each numeric/boolean persistence field. Those pins catch a
`|| → ??` swap on the exact pinned line, but miss:
  - a later re-assignment elsewhere in the function,
  - a migration helper that overrides after mapping,
  - a post-load normalization that resets picker fields,
  - a repairZoneData quirk that defaults valid values.

This file supplements (does NOT replace) those source pins with a real
behavioral harness. `tests/_runtime_harness/load_config_falsy.mjs`
extracts the live `zones = cfg.zones.map(z => ({...}))` block from
paint-booth-2-state-zones.js, runs it in a V8 sandbox with a realistic
falsy-value saved-config, and asserts every tracked field survived.

A negative-control mutation (swap `??` for `||` on pickerTolerance)
is run inside the harness to prove the test infrastructure actually
catches the regression it claims to catch.

Trust level of the combined coverage:
  - source pins in test_regression_save_load_repair_integrity.py:
    fast, cheap, catch exact-line swaps.
  - this behavioral test: slower, runs the live mapping, catches
    end-to-end regressions including downstream clobbering.
  - the negative control in the harness: self-validates that the
    behavioral test can still detect its target class of bug.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "load_config_falsy.mjs"


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
    # Exit 0 = all checks passed; 3 = field failures; others = crash.
    if proc.returncode not in (0, 3):
        pytest.fail(
            f"load_config_falsy harness crashed (exit {proc.returncode}):\n"
            f"stdout: {proc.stdout[:500]}\nstderr: {proc.stderr[:500]}"
        )
    return json.loads(proc.stdout), proc.returncode


@pytest.fixture(scope="module")
def harness():
    data, exit_code = _run_harness()
    return data


FIELDS_EXPECTED_FALSY = [
    ("pickerTolerance", 0),
    ("scale", 0),
    ("rotation", 0),
    ("patternOpacity", 0),
    ("patternIntensity", "0"),
    ("wear", 0),
    ("muted", False),
    ("baseStrength", 0),
    ("baseSpecStrength", 0),
    ("patternSpecMult", 0),
    ("patternFlipH", False),
    ("patternFlipV", False),
    ("baseRotation", 0),
    ("baseFlipH", False),
    ("baseFlipV", False),
    ("baseScale", 0),
    ("baseHueOffset", 0),
    ("baseSaturationAdjust", 0),
    ("baseBrightnessAdjust", 0),
]


@pytest.mark.parametrize("field,expected_value", FIELDS_EXPECTED_FALSY)
def test_load_config_preserves_falsy_value_behaviorally(
    harness, field, expected_value
):
    """Each persistence field that is LEGITIMATELY falsy in painter
    saves must round-trip through `zones = cfg.zones.map(...)`
    unchanged. If this fires, a `??`-vs-`||` regression happened
    somewhere in the mapping chain and a painter who saved the
    value as 0/false will get the default back on load.
    """
    checks = harness.get("field_checks", {})
    assert field in checks, (
        f"Harness did not report a check for {field!r}. "
        f"Either the field was removed from the mapping block or the "
        f"harness was not updated. Found: {sorted(checks.keys())}"
    )
    entry = checks[field]
    assert entry["ok"], (
        f"{field}: expected {entry['expected']!r} (reason: {entry['reason']}), "
        f"got {entry['got']!r}. "
        f"The zones.map block in loadConfigFromObj is clobbering this "
        f"falsy value — the painter's save will load with the wrong "
        f"value."
    )


def test_load_config_structural_fields_survive(harness):
    """Non-falsy structural fields (id, name, pattern id, colorMode)
    must round-trip exactly. Guards against an accidental `||`-vs-`??`
    swap on the string fields (which would be mostly harmless since
    non-empty strings are truthy, but empty strings would be clobbered).
    """
    checks = harness.get("structural_checks", {})
    failures = [k for k, v in checks.items() if not v["ok"]]
    assert not failures, (
        f"Structural fields failed round-trip: {failures}. "
        f"Full report: {checks}"
    )


def test_harness_negative_control_catches_regression(harness):
    """The harness mutates the mapping in-memory to swap `??` for `||`
    on pickerTolerance, then re-runs in a fresh sandbox. It must
    observe the regression (pickerTolerance=0 → 40). If this test
    fires, the behavioral test infrastructure itself has broken —
    the harness is passing even on a known-bad mutation.

    This test exists ENTIRELY to prove the test can still detect the
    class of bug it claims to guard against. Without it, all the other
    tests in this file could be silently green even if the real
    mapping regressed.
    """
    nc = harness.get("negative_control", {})
    assert nc.get("ran") is True, (
        f"Negative control did NOT run. Harness reports: {nc}. "
        f"Likely the `pickerTolerance ?? 40` literal moved or changed "
        f"shape — update the mutation site in "
        f"tests/_runtime_harness/load_config_falsy.mjs."
    )
    assert nc.get("caught_regression") is True, (
        f"Negative-control mutation (swap ?? for ||) did NOT produce "
        f"the expected regression. pickerTolerance passed through as "
        f"{nc.get('passed_through')!r} (expected 40). The harness is "
        f"not actually running the mutated block correctly — it's "
        f"giving false confidence. Fix the sandbox setup."
    )


def test_load_config_zone_count(harness):
    """A one-entry `cfg.zones` input must produce a one-entry `zones`
    output. Trivial structural check — guards against accidental
    filter/map type changes.
    """
    assert harness.get("zone_count") == 1, (
        f"Expected 1 zone, got {harness.get('zone_count')}"
    )
