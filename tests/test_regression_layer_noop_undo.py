from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start_marker: str, end_marker: str) -> str:
    start = CANVAS.index(start_marker)
    return CANVAS[start:CANVAS.index(end_marker, start)]


def test_layer_brush_undo_is_deferred_until_pixels_prove_they_changed():
    begin = _span("function _beginLayerPixelStroke", "window._beginLayerPixelStroke")
    commit = _span("function _commitLayerPaint()", "function _cancelLayerPaintStroke")
    assert "_pendingLayerPaintUndo" in begin
    assert "_pushLayerUndo(" not in begin
    assert "if (!pixelsChanged)" in commit
    assert "_pushLayerUndo(layer, _pendingLayerPaintUndo.label)" in commit
    assert commit.index("if (!pixelsChanged)") < commit.index("_pushLayerUndo(layer, _pendingLayerPaintUndo.label)")


def test_cancelled_healing_stroke_never_pushes_history_early():
    healing = _span("if (canvasMode === 'heal')", "if (canvasMode === 'pen')")
    assert "_beginLayerPixelStroke('Healing Brush', 'healing on layer')" in healing
    assert "_pushLayerUndo(" not in healing
    assert "_cancelLayerPaintStroke" in healing


def test_layer_target_is_pinned_for_the_whole_stroke():
    init = _span("function _initLayerPaintCanvas()", "function _beginLayerPixelStroke")
    commit = _span("function _commitLayerPaint()", "function _cancelLayerPaintStroke")
    assert "_activeLayerPaintLayerId = layer.id" in init
    assert "candidate.id === _activeLayerPaintLayerId" in commit


def test_erase_to_fully_transparent_layer_is_committed_and_undoable():
    commit = _span("function _commitLayerPaint()", "function _cancelLayerPaintStroke")
    empty = commit[commit.index("if (maxX < minX && !_hasOffCanvasArt)"):]
    assert "_pushLayerUndo(layer, _pendingLayerPaintUndo.label)" in commit
    assert "layer.img = emptyCanvas" in empty
    assert "layer.bbox = [0, 0, 1, 1]" in empty
    assert "return true" in empty


def test_pass_53_runtime_is_cache_busted_and_mirrored():
    assert "spb93-noop-undo-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
