"""HEENAN 5H OVERNIGHT — iter 9 behavioral proof for the DNA strip fix.

Pre-fix state: `_extractZoneDNA` built the `dna` object via `||` and
then ran a blanket strip that removed every value equal to `null`,
`false`, `0`, `''`, `'none'`, `'source'`, or `'normal'`. That combination
silently erased painter intent on fields where `0` was a legitimate
non-default value:
  - `baseColorStrength=0` (load-default 1) — "no base-color overlay"
  - `scale=0`, `baseScale=0`, etc. (default 1.0) — explicit degenerate
  - `secondBaseFractalScale=0` (default 24) — explicit flat scale
  - any `secondBase*` / `thirdBase*` / etc. strength fields where the
    `||` at the capture step promoted 0 to the DNA default before
    the strip layer even ran.

Painter-facing: copying DNA from a zone configured with any of the
above and pasting into a zone that had a different value silently
transferred the wrong setting.

Post-fix (this iter):
  1. Capture step: `||` → `??` for numeric/boolean fields on which
     falsy is legitimate-and-non-default.
  2. Strip step: blanket `val === 0 || val === false` replaced with
     a per-field `_DNA_DEFAULTS` lookup; a value is stripped only
     when it equals the field's canonical load-default.

This file drives `tests/_runtime_harness/dna_strip_preserves_intent.mjs`,
which extracts the live `_extractZoneDNA` function from source and
invokes it against three cases:
  A. Painter explicitly set baseColorStrength=0, scale=0, etc.
  B. Fields at their default values (should be stripped for compactness).
  C. Fields at arbitrary non-default values (should round-trip).
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "dna_strip_preserves_intent.mjs"


def _run_harness():
    if shutil.which("node") is None:
        pytest.skip("node not on PATH")
    assert HARNESS.exists()
    proc = subprocess.run(
        ["node", str(HARNESS)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode not in (0, 3):
        pytest.fail(
            f"harness crashed (exit {proc.returncode}):\n"
            f"stdout: {proc.stdout[:500]}\nstderr: {proc.stderr[:500]}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def harness():
    return _run_harness()


def test_dna_preserves_painter_zero_base_color_strength(harness):
    """`baseColorStrength=0` (no base-color overlay) must survive
    the DNA extract+strip path. Pre-fix it was silently stripped
    by the blanket `val === 0` rule, even though the load-default
    is 1.
    """
    A = harness.get("case_A_painter_zero", {})
    assert A.get("baseColorStrength_present"), (
        "baseColorStrength=0 was stripped from the DNA output — "
        "this is the pre-fix bug. The strip logic must use the "
        "per-field canonical default, not a blanket val===0 rule."
    )
    assert A.get("baseColorStrength_value") == 0, (
        f"baseColorStrength was captured but stored as "
        f"{A.get('baseColorStrength_value')!r}, not 0."
    )


def test_dna_preserves_painter_zero_scale(harness):
    """`scale=0` (explicit degenerate but legitimate override) must
    survive. The capture step's `||` was silently promoting 0 to
    1.0 BEFORE the strip layer could see it.
    """
    A = harness.get("case_A_painter_zero", {})
    assert A.get("scale_present"), (
        "scale=0 was stripped — either the capture step still uses "
        "`||` on scale or the strip logic regressed."
    )
    assert A.get("scale_value") == 0


def test_dna_preserves_painter_zero_second_base_family(harness):
    """Secondary-base overlay fields (scale=0, fractalScale=0) must
    survive the DNA round-trip.
    """
    A = harness.get("case_A_painter_zero", {})
    assert A.get("secondBaseScale_present"), (
        "secondBaseScale=0 stripped — fix regressed."
    )
    assert A.get("secondBaseFractalScale_present"), (
        "secondBaseFractalScale=0 stripped — fix regressed."
    )


def test_dna_strips_default_values_for_compactness(harness):
    """When a field's value EQUALS its canonical default, the strip
    step SHOULD remove it from the DNA output (DNA string stays compact).
    """
    B = harness.get("case_B_defaults", {})
    assert B.get("baseColorStrength_stripped"), (
        "baseColorStrength=1 (the default) was kept in DNA — "
        "compactness regression."
    )
    assert B.get("scale_stripped"), (
        "scale=1.0 (the default) was kept in DNA — compactness "
        "regression."
    )


def test_dna_preserves_arbitrary_non_default_values(harness):
    """Arbitrary non-default values (e.g. baseColorStrength=0.5,
    scale=2.0) must survive the round-trip unchanged.
    """
    C = harness.get("case_C_custom", {})
    assert C.get("baseColorStrength_kept"), (
        "baseColorStrength=0.5 not preserved in DNA."
    )
    assert C.get("scale_kept"), (
        "scale=2.0 not preserved in DNA."
    )


def test_dna_harness_reports_no_failures(harness):
    """Summary gate — any failure in the harness must surface here
    even if the individual tests above are updated.
    """
    failures = harness.get("failures", [])
    assert not failures, (
        "DNA harness reported failures:\n  " + "\n  ".join(failures)
    )
