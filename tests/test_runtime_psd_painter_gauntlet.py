"""TRUE FIVE-HOUR SHIFT runtime PSD painter gauntlet.

End-to-end-ish: builds a "PSD loaded" context (3 layers including a
locked one), then exercises the canvas mutators in sequence. Verifies:

  Step 1: Auto Levels on the sponsor layer routes through the layer
          path (push layer undo, init layer paint, commit layer paint),
          NOT the composite path. Toast mentions "layer".
  Step 2: Switching to a locked layer and re-running Auto Levels
          refuses + error toast + no mutation.
  Step 3: Trying to flip the canvas while PSD layers are loaded
          refuses + error toast + no mutation, no preview refresh.
  Step 4: Selection grow pushes a real zone undo (TF9 fix).
  Step 5: Posterize on sponsor layer same routing pattern as Step 1.
  Step 6: Invert on base layer routes the layer undo to L_base
          (correct layer-id targeting).

This is NOT a real PSD-file-load test; it is a runtime exercise of the
canvas helpers under realistic state. Real-file proof remains a
manual-painter-acceptance item per docs/PSD_PAINTER_GAUNTLET_OVERNIGHT.md.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "psd_painter_gauntlet.mjs"


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
        timeout=120,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"PSD painter gauntlet harness failed.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def gauntlet():
    return _run_harness()


def test_gauntlet_step1_auto_levels_on_sponsor_layer(gauntlet):
    """Auto Levels with sponsor layer selected routes to layer (TF1)."""
    r = gauntlet["step1_auto_levels_on_sponsor"]
    assert r["ok"], f"harness exception: {r.get('error')}"
    assert r["layer_undo_pushed"]
    assert r["layer_init_called"]
    assert r["layer_commit_called"]
    assert r["no_pixel_undo"]
    assert r["toast_mentions_layer"]


def test_gauntlet_step2_auto_levels_locked_refuses(gauntlet):
    """Auto Levels on locked layer refuses (TF1 lock guard)."""
    r = gauntlet["step2_auto_levels_on_locked"]
    assert r["ok"]
    assert r["no_layer_undo"]
    assert r["no_pixel_undo"]
    assert r["no_init"]
    assert r["error_toast_present"]


def test_gauntlet_step3_flip_canvas_refuses_with_psd_layers(gauntlet):
    """flipCanvasH refuses with PSD layers loaded (TF6)."""
    r = gauntlet["step3_flip_canvas_with_psd"]
    assert r["ok"]
    assert r["no_pixel_undo"]
    assert r["no_preview_trigger"]
    assert r["error_toast"]


def test_gauntlet_step4_grow_selection_pushes_zone_undo(gauntlet):
    """Selection grow pushes zone undo + actually grows mask (TF9)."""
    r = gauntlet["step4_grow_selection"]
    assert r["ok"]
    assert r["zone_undo_pushed"]
    assert r["mask_grew"]


def test_gauntlet_step5_posterize_on_sponsor_layer(gauntlet):
    """Posterize routes through layer (TF5)."""
    r = gauntlet["step5_posterize_on_sponsor"]
    assert r["ok"]
    assert r["layer_undo_pushed"]
    assert r["layer_init_called"]
    assert r["layer_commit_called"]
    assert r["no_pixel_undo"]


def test_gauntlet_step6_invert_targets_correct_layer(gauntlet):
    """Invert correctly targets L_base when L_base is selected (TF4 layer routing)."""
    r = gauntlet["step6_invert_on_base"]
    assert r["ok"]
    assert r["layer_undo_target_correct"], (
        "Invert pushed undo for the wrong layer — layer-id targeting broke"
    )
    assert r["layer_init_called"]
