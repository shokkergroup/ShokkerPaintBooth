from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start_marker: str, end_marker: str) -> str:
    start = CANVAS.index(start_marker)
    return CANVAS[start:CANVAS.index(end_marker, start)]


def test_adjustment_target_builds_offscreen_candidate_without_consuming_history():
    target = _span("function _getAdjustmentTarget", "function _commitAdjustment")
    assert "sourcePixels" in target
    assert "compositeCanvas: pc" in target
    assert "_pushLayerUndo(" not in target
    assert "pushPixelUndo(" not in target
    assert "return { canvas: pc" not in target


def test_adjustment_commit_compares_bytes_before_one_target_specific_undo():
    commit = _span("function _commitAdjustment", "function adjustBrightnessContrast")
    no_op = commit.index("if (!changed) {")
    layer_undo = commit.index("_pushLayerUndo(target.layer")
    pixel_undo = commit.index("pushPixelUndo(target.undoLabel")
    assert no_op < layer_undo
    assert no_op < pixel_undo
    assert "destination.getContext('2d', { willReadFrequently: true }).putImageData(candidate, 0, 0)" in commit
    assert "return true" in commit


def test_color_replace_no_match_never_pops_prior_history_or_destroys_redo():
    single = _span("function autoColorReplace(", "function autoColorReplaceAllLayers")
    all_layers = _span("function autoColorReplaceAllLayers", "window.autoColorReplaceAllLayers")
    assert "_layerUndoStack.pop" not in single
    assert "_layerUndoStack.pop" not in all_layers
    assert all_layers.index("if (totalCount === 0)") < all_layers.index("_pushLayerStackUndo('color replace (all layers)')")
    assert "pendingUpdates.push({ layer, canvas: c })" in all_layers


def test_pass_58_runtime_is_cache_busted_and_mirrored():
    assert "spb93-adjustment-transactions-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
