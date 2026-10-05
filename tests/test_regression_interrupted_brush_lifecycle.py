from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start_marker: str, end_marker: str) -> str:
    start = CANVAS.index(start_marker)
    return CANVAS[start:CANVAS.index(end_marker, start)]


def test_shared_cancel_releases_layer_and_every_transient_brush_state():
    lifecycle = _span("function _releaseActiveBrushStrokeState", "// All modes that show a brush cursor")
    cancel = _span("function _cancelActiveLayerBrushStroke", "window._cancelActiveLayerBrushStroke")
    assert "_cancelLayerPaintStroke()" in cancel
    assert "_releaseActiveBrushStrokeState()" in cancel
    for state in (
        "window.endHealingStroke",
        "window.SPBRecolorBrush?.endStroke",
        "_cloneStrokeSource = null",
        "resetSmudge()",
        "_resetPencilStroke()",
        "_resetBrushSpacing()",
        "window.resetBrushSmoothing",
        "window.resetBrushStabilizer",
        "window._spbStrokeSymmetryMode = null",
        "isDrawing = false",
    ):
        assert state in lifecycle


def test_escape_and_delete_cancel_without_popping_previous_history():
    escape_start = CANVAS.index("// Fix: if the painter is currently drawing a layer stroke")
    escape = CANVAS[escape_start:CANVAS.index("_selectedLayerId = null", escape_start)]
    delete = _span("function deleteLayer(layerId)", "function addBlankLayer")
    for block in (escape, delete):
        assert "_cancelActiveLayerBrushStroke" in block
        assert "_layerUndoStack.pop" not in block
        assert "_activeLayerCanvas = null" not in block


def test_window_blur_finishes_through_mouseup_lifecycle_instead_of_leaking_buffer():
    blur = _span("window.addEventListener('blur'", "canvas.onmousedown = function")
    assert "_finishActiveBrushStroke()" in blur
    assert "window._activeLayerCanvas = null" not in blur
    assert "isDrawing = false" in blur  # defensive non-brush fallback only


def test_pan_takeover_finishes_active_brush_before_scrolling():
    start = CANVAS.index("// Pan takeover is another stroke exit")
    pan = CANVAS[start:CANVAS.index("rectStart = null", start)]
    assert "_finishActiveBrushStroke()" in pan
    assert "if (isDrawing" in pan


def test_pass_57_runtime_is_cache_busted_and_mirrored():
    assert "spb93-interrupted-stroke-lifecycle-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
