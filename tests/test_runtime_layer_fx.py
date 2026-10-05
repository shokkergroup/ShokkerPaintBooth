"""TRUE FIVE-HOUR SHIFT runtime-proof for TF18-TF19 (layer-fx undo).

pasteLayerFx (TF18) and applyQuickFx (TF19) in paint-booth-layer-flow.js
both mutated `L.effects` (drop shadow, glow, stroke, color overlay, bevel)
without pushing an undo entry. Painters could not Ctrl+Z to revert effect
operations.

Fix: both now push `_pushLayerStackUndo('Paste layer effects')` and
`_pushLayerStackUndo('Apply quick FX: <preset>')` BEFORE mutating
`L.effects`. Runtime harness verifies the spy is called with the right
label.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "layer_fx.mjs"


def _run_harness():
    if shutil.which("node") is None:
        pytest.skip("node not on PATH; runtime harness requires Node 18+")
    if not HARNESS.exists():
        pytest.fail(f"missing: {HARNESS}")
    proc = subprocess.run(
        ["node", str(HARNESS)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"layer_fx harness failed.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def harness():
    return _run_harness()


def test_runtime_TF18_paste_layer_fx_pushes_undo(harness):
    """RUNTIME: pasteLayerFx must push a layer-stack undo entry before
    overwriting L.effects with the clipboard payload."""
    r = harness["tf18_paste_layer_fx"]
    assert r["ok"]
    assert r["return_value"] is True, "pasteLayerFx returned non-True for happy path"
    assert r["layer_stack_undo_pushed"], (
        "pasteLayerFx did not push a layer-stack undo entry — TF18 fix did not land"
    )
    assert "paste" in r["undo_label"].lower()
    assert r["recomposite_called"]
    assert r["preview_triggered"]
    assert r["effects_changed"]


def test_runtime_TF19_apply_quick_fx_pushes_undo(harness):
    """RUNTIME: applyQuickFx must push a layer-stack undo entry before
    merging the preset into L.effects. Label must include the preset name
    so the painter sees a meaningful undo entry in the history."""
    r = harness["tf19_apply_quick_fx"]
    assert r["ok"]
    assert r["layer_stack_undo_pushed"], (
        "applyQuickFx did not push a layer-stack undo entry — TF19 fix did not land"
    )
    # Label should include the preset name
    assert "Drop Shadow" in r["undo_label"], (
        f"undo label missing preset name: {r['undo_label']}"
    )
    assert r["recomposite_called"]
    assert r["preview_triggered"]
    assert r["toast_fired"]
