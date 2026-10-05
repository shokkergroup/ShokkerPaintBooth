"""HEENAN 5H OVERNIGHT — iter 10 cross-feature integration test.

Stitches together the individually-verified fixes from iters 1, 8,
and 9 into a single end-to-end painter-workflow roundtrip:

  Step 1: Painter configures a zone with tolerance=0, wear=0,
          muted=false — persistence-critical falsy values.
  Step 2: exportPreset serializes the zone into a .shokker preset
          object. (iter 8 fix: `||` → `??` on numeric/boolean fields.)
  Step 3: Recipient calls applyPreset(preset_object) via the
          polymorphic dispatcher. (iter 1 fix: dispatcher replaces
          the duplicate-definition shadowing bug; object-form helper
          uses `??`.)
  Step 4: SEPARATE DNA chain — a zone with baseColorStrength=0
          (painter-explicit "no base-color overlay") has _extractZoneDNA
          serialize its state. (iter 9 fix: capture uses `??`, strip
          uses per-field canonical-default lookup.)

Unlike the individual iter harnesses, this test proves the fixes
COMPOSE correctly — that a bug fix in one layer isn't silently
undone by a defect in a downstream layer.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "overnight_integration_roundtrip.mjs"


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
            f"stdout: {proc.stdout[:600]}\nstderr: {proc.stderr[:600]}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def harness():
    return _run_harness()


def test_preset_export_preserves_falsy_persistence_fields(harness):
    """Step 2 of the integration: exportPreset serializes a zone's
    falsy-legitimate values unchanged. Covers iter 8's `||` → `??` fix.
    """
    s2 = harness["step2_export_preset"]
    assert s2["pickerTolerance"] == 0, (
        f"pickerTolerance=0 became {s2['pickerTolerance']!r} in export"
    )
    assert s2["wear"] == 0
    assert s2["muted"] is False


def test_preset_apply_recipient_preserves_falsy_values(harness):
    """Step 3 of the integration: applyPreset dispatches to the
    object-form helper, which uses `??` to preserve falsy values.
    Covers iter 1's polymorphic dispatcher + falsy-preservation fix.
    """
    s3 = harness["step3_recipient_zone"]
    assert s3["pickerTolerance"] == 0, (
        f"Recipient got pickerTolerance={s3['pickerTolerance']!r}; "
        f"painter's 0 (exact-match selector) was lost on load."
    )
    assert s3["wear"] == 0
    assert s3["muted"] is False


def test_preset_apply_recipient_preserves_structural_fields(harness):
    """Step 3 continued: non-persistence fields (base id, pattern id,
    spec_pattern_stack) must also round-trip correctly. Guards against
    a collateral regression that drops structural fields.
    """
    s3 = harness["step3_recipient_zone"]
    assert s3["base"] == "gloss", "base id lost on preset apply"
    assert s3["pattern"] == "carbon_fiber", "pattern id lost on preset apply"
    assert s3["specPatternStack_length"] == 1, (
        f"spec pattern stack lost; got length {s3['specPatternStack_length']}"
    )


def test_dna_extract_preserves_painter_zero_on_non_zero_default_field(harness):
    """Step 4 of the integration: _extractZoneDNA capture and strip
    both preserve a painter-set `baseColorStrength=0` even though the
    field's canonical default is 1. Covers iter 9's two-part fix
    (capture `||` → `??` AND per-field default-table strip).
    """
    s4 = harness["step4_dna_payload"]
    assert s4["has_baseColorStrength"] is True, (
        "baseColorStrength=0 was stripped from DNA — iter 9 regression "
        "(painter's 'no base-color overlay' intent lost on DNA share)."
    )
    assert s4["baseColorStrength"] == 0, (
        f"baseColorStrength stored as {s4['baseColorStrength']!r}, not 0."
    )


def test_dna_extract_preserves_arbitrary_non_default(harness):
    """Step 4 continued: arbitrary non-default values (e.g. scale=0.5)
    survive the DNA capture + strip unchanged.
    """
    s4 = harness["step4_dna_payload"]
    assert s4["has_scale"] is True
    assert s4["scale"] == 0.5


def test_overnight_integration_composition_is_clean(harness):
    """All-or-nothing gate for the composed pipeline. If any of the
    individual iter 1/8/9 fixes silently undoes or shadows another,
    the harness's failures[] array collects the problems.
    """
    failures = harness.get("failures", [])
    assert not failures, (
        "Cross-feature integration failed:\n  " + "\n  ".join(failures)
    )
