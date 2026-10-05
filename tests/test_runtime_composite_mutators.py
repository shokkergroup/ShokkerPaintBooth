"""TRUE FIVE-HOUR SHIFT runtime-proof harness for composite mutators TF1-TF5.

This is RUNTIME proof — not "the string appears in the source." Each of
autoLevels / autoContrast / desaturateCanvas / invertCanvasColors / posterize
is loaded from paint-booth-3-canvas.js and EXECUTED inside Node V8 against
three scenarios:

  1. composite     — no PSD layer selected; mutator should write the composite
                     buffer + push pixel undo + trigger preview refresh.
  2. editable_layer — an editable PSD layer is selected; mutator MUST route
                      through the layer (push layer undo, init layer canvas,
                      commit layer paint) and MUST NOT write the composite.
  3. locked         — a locked layer is selected; mutator MUST refuse with
                      an explicit error toast and write NO buffer.

All three scenarios are proven for all five mutators. If a future refactor
strips locked-guard or active-layer routing, the matching scenario will fail.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "composite_mutators.mjs"

FUNCS = ("autoLevels", "autoContrast", "desaturateCanvas", "invertCanvasColors", "posterize")


def _run_harness():
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
            f"Runtime harness exited non-zero.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def harness():
    return _run_harness()


# ── locked scenario: every mutator must refuse + toast ────────────────────────
@pytest.mark.parametrize("func", FUNCS)
def test_runtime_TF_locked_layer_refuses(harness, func):
    """RUNTIME (TF1-TF5): when a locked PSD layer is selected, the mutator
    refuses with an error toast and writes neither the composite nor the
    layer buffer. No undo entries are pushed."""
    r = harness[func]["locked"]
    assert r["ok"], f"harness exception: {r.get('error')}"
    assert r["composite_mutated"] is False, f"{func} mutated composite under locked layer"
    assert r["layer_mutated"] is False, f"{func} mutated layer under locked layer"
    assert r["pushPixelUndo"] == []
    assert r["_pushLayerUndo"] == []
    assert r["_initLayerPaintCanvas_count"] == 0
    assert r["_commitLayerPaint_count"] == 0
    assert r["triggerPreviewRender_count"] == 0
    # Must surface an error toast naming the lock.
    assert any(t[1] is True and "locked" in t[0].lower() for t in r["showToast"]), (
        f"{func}: locked scenario should show an error toast about locked layer"
    )


# ── editable_layer scenario: route to layer, don't touch composite ────────────
@pytest.mark.parametrize("func", FUNCS)
def test_runtime_TF_editable_layer_routes_to_layer(harness, func):
    """RUNTIME (TF1-TF5): when an editable PSD layer is selected, the
    mutator pushes a LAYER undo (not pixel undo), inits the layer paint
    canvas, mutates LAYER pixels (composite untouched), commits layer paint,
    and does NOT trigger a composite preview refresh (commit handles it)."""
    r = harness[func]["editable_layer"]
    assert r["ok"], f"harness exception: {r.get('error')}"
    assert r["composite_mutated"] is False, (
        f"{func} mutated composite under editable layer — silent data divergence bug"
    )
    assert r["layer_mutated"] is True, f"{func} did not mutate the layer"
    assert r["pushPixelUndo"] == [], (
        f"{func} pushed pixel undo while a layer was the target — should push layer undo"
    )
    assert len(r["_pushLayerUndo"]) == 1
    layer_undo = r["_pushLayerUndo"][0]
    assert layer_undo[0] == "L1"
    assert "on layer" in layer_undo[1].lower()
    assert r["_initLayerPaintCanvas_count"] == 1
    assert r["_commitLayerPaint_count"] == 1
    assert r["triggerPreviewRender_count"] == 0, (
        f"{func} fired triggerPreviewRender on layer path — _commitLayerPaint already "
        "handles recompositeFromLayers; double-trigger would be wasteful churn"
    )
    # Toast should mention "to layer" / "on layer" (parity with brush family).
    assert any("layer" in t[0].lower() for t in r["showToast"]), (
        f"{func}: editable-layer scenario should toast about the layer target"
    )


# ── composite scenario: no layer ⇒ mutate composite, fire preview refresh ─────
@pytest.mark.parametrize("func", FUNCS)
def test_runtime_TF_composite_path_unchanged(harness, func):
    """RUNTIME (TF1-TF5 + W5-W9): when no PSD layer is selected, the mutator
    falls through to the composite path: pushes pixel undo, mutates composite
    pixels, triggers preview refresh. This is the prior-shift W5-W9 behavior
    confirmed under runtime, not just structurally."""
    r = harness[func]["composite"]
    assert r["ok"], f"harness exception: {r.get('error')}"
    assert r["composite_mutated"] is True, f"{func} did not mutate composite"
    assert r["layer_mutated"] is False
    assert len(r["pushPixelUndo"]) == 1
    assert r["_pushLayerUndo"] == []
    assert r["_initLayerPaintCanvas_count"] == 0
    assert r["_commitLayerPaint_count"] == 0
    assert r["triggerPreviewRender_count"] == 1, (
        f"{func} composite path must call triggerPreviewRender — prior-shift W5-W9 fix"
    )


# ── identity check: invertCanvasColors actually inverts ───────────────────────
def test_runtime_invert_actually_inverts(harness):
    """RUNTIME ALGEBRA: starting pixels were RGB(200,50,100); inverted is
    (255-200, 255-50, 255-100) = (55, 205, 155). Alpha untouched."""
    r = harness["invertCanvasColors"]["composite"]
    assert r["composite_after"][:3] == [55, 205, 155]
    assert r["composite_after"][3] == 255  # alpha untouched


# ── identity check: desaturate yields gray ────────────────────────────────────
def test_runtime_desaturate_yields_gray(harness):
    """RUNTIME ALGEBRA: starting pixels were RGB(200,50,100); luminance =
    0.299*200 + 0.587*50 + 0.114*100 = 100.55 → 101 (rounded), written to
    all three channels. R/G/B should all collapse to 101."""
    r = harness["desaturateCanvas"]["composite"]
    assert r["composite_after"][:3] == [101, 101, 101]
