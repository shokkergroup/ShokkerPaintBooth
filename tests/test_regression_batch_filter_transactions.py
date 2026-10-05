from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, f"missing {name}"
    start = match.end()
    depth = 1
    index = start
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[start : index - 1]


def test_pass_97_transaction_refuses_flattened_fallthrough_and_captures_before():
    body = _function_body("_beginBatchPixelFilter")
    guard = body.index("if (!layer && layeredDocument)")
    init = body.index("_initLayerPaintCanvas")
    capture = body.index("before: new Uint8ClampedArray(paintImageData.data)")
    assert guard < init < capture
    assert "_diagnoseLayerPaintFail" in body
    assert "_settleActiveLayerStrokeBeforeTargetChange" in body
    assert "selection: _activeSelectionMask(pc.width, pc.height)" in body


def test_pass_97_history_is_created_only_after_difference_proof():
    body = _function_body("_finishBatchPixelFilter")
    clip = body.index("applyMask(data, tx.before")
    proof = body.index("if (!changed)")
    layer_history = body.index("_pushLayerUndo")
    pixel_history = body.index("pushPixelUndo")
    assert clip < proof < layer_history < pixel_history
    assert "window.SPBSelectionClip?.applyMask" in body
    assert "_cancelLayerPaintStroke" in body
    assert "data.set(tx.before)" in body
    assert "data.set(after)" in body


def test_pass_97_all_batch_filters_use_selection_and_transaction_boundary():
    for function_name in (
        "autoLevels",
        "autoContrast",
        "desaturateCanvas",
        "invertCanvasColors",
        "posterize",
    ):
        body = _function_body(function_name)
        assert "_beginBatchPixelFilter" in body, function_name
        assert "selection = tx.selection" in body, function_name
        assert "selection[i >> 2] === 0" in body, function_name
        assert "return _finishBatchPixelFilter(tx)" in body, function_name
        assert "pushPixelUndo" not in body, function_name
        assert "_pushLayerUndo" not in body, function_name


def test_pass_97_histogram_filters_measure_only_selected_opaque_pixels():
    for function_name in ("autoLevels", "autoContrast"):
        body = _function_body(function_name)
        gate = "if (d[i+3] === 0 || (selection && selection[i >> 2] === 0)) continue;"
        assert body.count(gate) == 2, function_name


def test_pass_97_posterize_levels_are_safe_and_bounded():
    body = _function_body("posterize")
    assert "Math.max(2, Math.min(256" in body


def test_pass_97_runtime_is_cache_busted():
    assert "spb93-batch-filter-transactions-20260717" in HTML
    assert "spb93-layer-selection-clip-20260717" in HTML
