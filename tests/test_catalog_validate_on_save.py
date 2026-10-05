"""HEENAN H4HR-VALIDATE-ON-SAVE — catalog drift catch at write time.

Currently `validateFinishData()` runs once at boot (via the
`setTimeout(...)` in `paint-booth-0-finish-data.js`). If a refactor
breaks the catalog (phantom group entry, duplicate name, etc.) it gets
caught at LOAD time — which means a CI run, a dev's pytest pass, or
worst-case a painter loading the broken build.

This pytest runs the validator every test session. It's the closest we
can get to "save-time validation" without modifying the editor toolchain
itself. Combined with the auto-boot validator, the catalog now has TWO
trust gates:
  1. Boot-time (browser): drift surfaces in dev console.
  2. Test-time (pytest): drift surfaces in CI / dev `pytest`.

Any new catalog edit that breaks structure fails fast.

This file also exposes a callable so other tests / hooks can re-validate
on demand.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "validate_finish_data.mjs"


def _run_validator():
    """Re-run validateFinishData against the current catalog. Returns dict."""
    if shutil.which("node") is None:
        pytest.skip("node not on PATH")
    proc = subprocess.run(
        ["node", str(HARNESS)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"validate harness failed.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def validation():
    return _run_validator()


def test_VALIDATE_ON_SAVE_zero_problems(validation):
    """The validator must report zero problems on every test session.
    Catches any catalog drift introduced by a refactor / rename / new
    entry — at TEST time, not painter-load time."""
    n = validation["problem_count"]
    assert n == 0, (
        f"validateFinishData reports {n} problems. Sample:\n  "
        + "\n  ".join(validation.get("problems", [])[:10])
    )


def test_VALIDATE_ON_SAVE_no_phantoms(validation):
    """Per-class breakdown so the failure message is actionable."""
    counts = validation["counts"]
    for k in ("phantom_base_group", "phantom_pattern_group",
              "phantom_spec_group", "cross_registry_pattern_group"):
        assert counts[k] == 0, (
            f"{k} = {counts[k]}; a group references an id that does not exist "
            f"in its registry. Painter sees a blank picker tile."
        )


def test_VALIDATE_ON_SAVE_no_duplicate_names(validation):
    """Duplicate display-names = picker shows two tiles with same label."""
    counts = validation["counts"]
    for k in ("duplicate_pattern_name", "duplicate_spec_name"):
        assert counts[k] == 0, f"{k} = {counts[k]}; rename to disambiguate."


def test_VALIDATE_ON_SAVE_no_ungrouped(validation):
    """Ungrouped entries land in a Misc tab — silent UX dead-end."""
    counts = validation["counts"]
    total_ungrouped = (counts["ungrouped_base"]
                       + counts["ungrouped_pattern"]
                       + counts["ungrouped_spec"])
    assert total_ungrouped == 0, (
        f"{total_ungrouped} ungrouped entries (BASE/PATTERN/SPEC). "
        f"Add to the appropriate group in BASE_GROUPS / PATTERN_GROUPS / "
        f"SPEC_PATTERN_GROUPS / SPECIAL_GROUPS."
    )


def test_VALIDATE_ON_SAVE_no_missing_metadata(validation):
    """desc < 20 chars or missing swatch fails the entry's polish bar."""
    counts = validation["counts"]
    assert counts["missing_desc"] == 0, f"missing_desc = {counts['missing_desc']}"
    assert counts["missing_swatch"] == 0, f"missing_swatch = {counts['missing_swatch']}"
