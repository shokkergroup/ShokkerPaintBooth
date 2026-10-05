"""SPB-93 Pass 146: empty/matching selection commands preserve history."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_source(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start, depth, index = match.start(), 0, match.start()
    while index < len(CANVAS):
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
            if depth == 0 and index > match.end():
                return CANVAS[start : index + 1]
        index += 1
    raise AssertionError(name)


def test_pass_146_layer_clear_candidate_precedes_cut_and_transform_history():
    helper = _function_source("_clearSelectionFromLayer")
    assert "opts.deferCommit" in helper
    assert "return { canvas: tmpCanvas, cleared: cleared }" in helper
    assert "if (cleared > 0) layer.img = tmpCanvas" in helper
    for name, history in (("cutSelection", "_pushLayerUndo"), ("liftSelectionToNewLayer", "_pushLayerStackUndo")):
        source = _function_source(name)
        candidate = source.index("{ deferCommit: true }")
        refusal = source.index("if (!candidate || !candidate.cleared)", candidate)
        history_at = source.index(history, refusal)
        assert candidate < refusal < history_at


def test_pass_146_fill_and_delete_use_pending_layer_history_and_composite_candidates():
    fill = _function_source("fillSelectionWithColor")
    delete = _function_source("deleteSelection")
    for source, label in ((fill, "fill selection"), (delete, "delete selection")):
        assert f"_beginLayerPixelStroke" in source
        assert label in source
        assert "new Uint8ClampedArray(paintImageData.data)" in source
        no_change = source.index("if (!count)")
        pixel_history = source.index("pushPixelUndo(", no_change)
        assert no_change < pixel_history
    assert "_pushLayerUndo(" not in fill
    assert "_pushLayerUndo(" not in delete
    assert "Alpha Lock protects this Layer" in delete
    assert "alphaMask" in fill


def test_pass_146_runtime_is_cache_busted():
    assert "spb93-selection-noop-history-20260717" in HTML
    assert re.search(r'src="paint-booth-3-canvas\.js\?v=[^"\s]+', HTML)
    assert "spb93-selection-command-routing-20260717" in HTML
