"""TRUE FIVE-HOUR SHIFT runtime-proof for TF6-TF8.

flipCanvasH / flipCanvasV / rotateCanvas90 are destructive composite-only
operations. recompositeFromLayers (canvas.js:10566) clears the canvas and
redraws every PSD layer from layer.img — meaning any composite-only
flip/rotate is overwritten the moment the next paint commit, layer
visibility toggle, or stack change fires recomposite.

Pre-fix this was a silent-drop bug. The TF6-TF8 fix shipped this shift
refuses the operation with an explicit error toast when PSD layers are
loaded and points the painter to the layer-level transform instead.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "canvas_geometry.mjs"

FUNCS = ("flipCanvasH", "flipCanvasV", "rotateCanvas90")


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
            f"Canvas geometry harness exited non-zero.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def harness():
    return _run_harness()


@pytest.mark.parametrize("func", FUNCS)
def test_runtime_TF_canvas_op_refuses_with_psd_layers(harness, func):
    """RUNTIME (TF6-TF8): with PSD layers loaded, the canvas-level
    flip/rotate must refuse the operation and surface an explicit error
    toast. No undo entry, no preview refresh, no mutation — preventing the
    silent-drop where recompositeFromLayers would overwrite the rotation."""
    r = harness[func]["psd_layers"]
    assert r["ok"], f"harness exception: {r.get('error')}"
    assert r["pushPixelUndo"] == [], (
        f"{func} pushed pixel undo while PSD layers were loaded — fix didn't bail"
    )
    assert r["triggerPreviewRender_count"] == 0, (
        f"{func} fired preview refresh on a refused operation"
    )
    # Must surface an error toast that mentions PSD layers or Layer ▸ menu.
    error_toasts = [t for t in r["showToast"] if t[1] is True]
    assert error_toasts, f"{func} silently bailed without toasting"
    msg = error_toasts[0][0].lower()
    assert "psd layers" in msg or "layer" in msg, (
        f"{func} toast must explain why it refused: {error_toasts[0][0]}"
    )


@pytest.mark.parametrize("func", FUNCS)
def test_runtime_TF_canvas_op_works_without_psd_layers(harness, func):
    """RUNTIME (TF6-TF8): without PSD layers loaded, the operation
    proceeds normally — pushes pixel undo, fires preview refresh, success
    toast. Confirms the guard does not over-block."""
    r = harness[func]["no_layers"]
    assert r["ok"], f"harness exception: {r.get('error')}"
    assert len(r["pushPixelUndo"]) == 1, f"{func} did not push pixel undo"
    assert r["triggerPreviewRender_count"] >= 1, f"{func} did not fire preview refresh"
    success_toasts = [t for t in r["showToast"] if t[1] is False]
    assert success_toasts, f"{func} did not surface a success toast"
