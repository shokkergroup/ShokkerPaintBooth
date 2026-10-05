from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start_marker: str, end_marker: str) -> str:
    start = CANVAS.index(start_marker)
    return CANVAS[start:CANVAS.index(end_marker, start)]


def test_layer_target_changes_use_shared_brush_lifecycle_without_popping_history():
    settle = _span("function _settleActiveLayerStrokeBeforeTargetChange", "function selectPSDLayer")
    select = _span("function selectPSDLayer", "function deselectPSDLayer")
    deselect = _span("function deselectPSDLayer", "window.deselectPSDLayer")
    assert "window._finishActiveBrushStroke()" in settle
    assert "_cancelLayerPaintStroke()" in settle
    assert "_settleActiveLayerStrokeBeforeTargetChange()" in select
    assert "_settleActiveLayerStrokeBeforeTargetChange()" in deselect
    for block in (settle, select, deselect):
        assert "_layerUndoStack.pop" not in block
        assert "_activeLayerCanvas = null" not in block


def test_clone_source_is_owned_by_the_layer_that_was_sampled():
    clone_contract = _span("function _cloneSourceLayerId", "function _isCloneStampAligned")
    clone_paint = _span("function paintCloneStroke", "function drawCloneSourceIndicator")
    clone_ui = _span("} else if (canvasMode === 'clone')", "} else if (canvasMode === 'heal')")
    assert "layerId: _cloneSourceLayerId()" in clone_contract
    assert "_cloneSource.layerId === _cloneSourceLayerId()" in clone_contract
    assert "_hasCloneSourceForActiveLayer()" in clone_paint
    assert "_hasCloneSourceForActiveLayer()" in clone_ui
    assert "Alt+Click this layer" in CANVAS


def test_pass_56_runtime_is_cache_busted_and_mirrored():
    assert "spb93-layer-switch-lifecycle-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
