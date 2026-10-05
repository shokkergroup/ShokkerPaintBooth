"""TRUE FIVE-HOUR SHIFT runtime-proof for TF12-TF14 (finish registry truth).

TF12 — phantom BASE_GROUPS purge: 9 entries pointed at ids that don't
       exist in BASES. Picker rendered blank tiles.
TF13 — duplicate PATTERN names disambiguated: 4 pairs of patterns shared
       a display name. Painters saw two of the same tile in the picker.
TF14 — duplicate SPEC_PATTERN names disambiguated: same problem in spec
       patterns. 4 pairs disambiguated.

This test runs validateFinishData() in real Node V8 against the live
catalog and asserts the counts are 0 for each fixed category.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "validate_finish_data.mjs"


def _run_validator():
    if shutil.which("node") is None:
        pytest.skip("node not on PATH; runtime harness requires Node 18+")
    if not HARNESS.exists():
        pytest.fail(f"runtime harness missing: {HARNESS}")
    proc = subprocess.run(
        ["node", str(HARNESS)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"validateFinishData harness exited non-zero.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def validation():
    return _run_validator()


def test_runtime_TF12_no_phantom_base_groups(validation):
    """RUNTIME: BASE_GROUPS must not reference any id that does not exist
    in the BASES array. Pre-fix there were 9 phantoms — picker rendered
    blank tiles when painter clicked them. Fix removed them; if anyone
    re-adds a phantom, this fires."""
    counts = validation["counts"]
    assert counts["phantom_base_group"] == 0, (
        f"phantom_base_group regressed to {counts['phantom_base_group']} — "
        f"some BASE_GROUPS entry references an id not in BASES"
    )


def test_runtime_TF13_no_duplicate_pattern_names(validation):
    """RUNTIME: PATTERNS must not have two entries sharing a display name.
    Pre-fix there were 4 pairs — painter saw the same tile name twice in
    the same picker tab and could not tell them apart."""
    counts = validation["counts"]
    assert counts["duplicate_pattern_name"] == 0, (
        f"duplicate_pattern_name regressed to {counts['duplicate_pattern_name']} — "
        f"two PATTERN entries share a display name"
    )


def test_runtime_TF14_no_duplicate_spec_pattern_names(validation):
    """RUNTIME: SPEC_PATTERNS must not have two entries sharing a display
    name. Same UX bug as TF13 in the spec-pattern picker."""
    counts = validation["counts"]
    assert counts["duplicate_spec_name"] == 0, (
        f"duplicate_spec_name regressed to {counts['duplicate_spec_name']} — "
        f"two SPEC_PATTERN entries share a display name"
    )


def test_runtime_TF12_TF14_no_phantom_or_cross_registry_groups(validation):
    """RUNTIME (broader catch): no group of any registry references an
    id that doesn't exist in the matching registry. Phantom + cross-
    registry both sum to 0 for a clean catalog."""
    counts = validation["counts"]
    total = (counts["phantom_base_group"]
             + counts["phantom_pattern_group"]
             + counts["phantom_spec_group"]
             + counts["cross_registry_pattern_group"])
    assert total == 0, f"registry phantom/cross-registry total = {total}, expected 0"
