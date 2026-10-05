"""HEENAN 5H OVERNIGHT — iter 1 runtime proof.

Drives `tests/_runtime_harness/apply_preset_dispatch.mjs`, which extracts
the live `applyPreset` dispatcher + helpers from `paint-booth-2-state-zones.js`
and runs them in a stubbed V8 sandbox. Asserts on actual behaviour, not on
source-text shape.

What this proves (Pillman's hostile QA survived, Hennig's final gate passed):
  1. The preset-gallery path (`applyPreset('some_id')`) actually dispatches
     to the ID-form helper and loads zones. Before the fix, this path was
     silently broken by JS function-declaration hoisting.
  2. The .shokker file-import path (`applyPreset({zones:[...]})`) dispatches
     to the object-form helper.
  3. Persistence fields that are legitimately falsy — pickerTolerance=0,
     wear=0, muted=false, scale=1.0 — round-trip through the object path
     instead of being silently replaced by the default.
  4. Unknown preset IDs, null, undefined, numbers, and other junk inputs
     are silent no-ops (no crash, no painter data loss).
  5. The pre-fix bug is reproduced by calling the object-form helper
     directly with a string arg — proving the fix addressed a real defect.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "apply_preset_dispatch.mjs"


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
    if proc.returncode != 0:
        pytest.fail(
            f"apply_preset_dispatch harness failed (exit {proc.returncode})\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def harness():
    return _run_harness()


# --- Gallery path (preset ID form, used by preset gallery card click) ---

def test_gallery_path_loads_zones(harness):
    assert harness["gallery_throw"] is None, (
        f"applyPreset('known_id') threw: {harness['gallery_throw']}"
    )
    assert harness["gallery_loads_zones"] == 2, (
        f"Gallery preset loaded {harness['gallery_loads_zones']} zones, expected 2"
    )
    assert harness["gallery_zone_names"] == ["Zone A", "Zone B"]


def test_gallery_path_unknown_id_is_silent_noop(harness):
    """Calling with an id not in PRESETS must neither throw nor
    mutate existing zone state.
    """
    assert harness["unknown_id_throw"] is None
    assert harness["unknown_id_zones_after"] == 1, (
        "unknown-id call clobbered existing zones"
    )


# --- Object path (.shokker file import) ---

def test_object_path_loads_zones(harness):
    assert harness["object_throw"] is None, (
        f"applyPreset({{zones:[...]}}) threw: {harness['object_throw']}"
    )
    assert harness["object_loads_zones"] == 1


def test_object_path_preserves_falsy_picker_tolerance(harness):
    """A preset authored with `pickerTolerance: 0` (exact-match color
    selector) must round-trip as 0, not be silently replaced by 40.
    This is the main bug the `|| → ??` switch fixed.
    """
    assert harness["object_tolerance_preserved"] == 0, (
        f"pickerTolerance=0 became "
        f"{harness['object_tolerance_preserved']!r} — `|| 40` regression"
    )


def test_object_path_preserves_falsy_wear(harness):
    assert harness["object_wear_preserved"] == 0


def test_object_path_preserves_falsy_muted(harness):
    assert harness["object_muted_preserved"] is False


def test_object_path_preserves_scale(harness):
    # Scale=1.0 in JS becomes 1 after serialization; both are numeric 1.
    assert harness["object_scale_preserved"] in (1, 1.0)


def test_object_path_empty_zones_array_is_safe(harness):
    assert harness["empty_object_throw"] is None


# --- Junk-input robustness ---

def test_null_and_undefined_inputs_are_silent_noop(harness):
    assert harness["null_undefined_throw"] is None
    # The dispatcher console.warns on each unrecognized input.
    assert harness["null_undefined_warn_count"] >= 2


def test_integer_input_is_silent_noop(harness):
    """applyPreset(42) must not crash. Before the fix, this would have
    hit the object-form function and thrown on `preset.zones.map`.
    """
    assert harness["int_throw"] is None


# --- Pre-fix bug reproduction (Pillman's proof the fix was real) ---

def test_prefix_bug_is_reproduced_by_bypassing_dispatcher(harness):
    """If we call `_applyPresetFromObject` directly with a string arg
    (simulating the pre-fix hoisting behavior), it must throw. This
    confirms the pre-fix state really was broken — the dispatcher is
    doing real work, not just shuffling names.
    """
    assert harness["prefix_sim_threw"] is True, (
        "Calling the object-form helper with a string DIDN'T throw. "
        "Either the helper is now accidentally polymorphic (masking "
        "the bug) or the harness didn't reach the throwing line. "
        "Verify the dispatcher is actually routing by typeof."
    )
    # Error message should reference the TypeError on `.map` or `.length`
    # or similar — we just verify there IS an error string.
    assert "TypeError" in harness.get("prefix_sim_error", "")
