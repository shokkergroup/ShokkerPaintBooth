from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start: str, end: str) -> str:
    begin = CANVAS.index(start)
    return CANVAS[begin : CANVAS.index(end, begin)]


def _function_body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
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


def test_pass_98_adjustments_refuse_layered_composite_fallthrough():
    body = _function_body("_getAdjustmentTarget")
    assert "const layeredDocument = _psdLayersLoaded" in body
    assert "if (layeredDocument)" in body
    assert "needs an editable Layer" in body
    assert body.index("if (layeredDocument)") < body.index("ctx.drawImage(pc, 0, 0)")


def test_pass_98_adjustment_target_captures_selection_and_layer_origin():
    body = _function_body("_getAdjustmentTarget")
    assert body.count("selectionMask: _activeSelectionMask(pc.width, pc.height)") == 2
    assert "getLayerCanvasOrigin(layer)" in body
    assert "selectionWidth: pc.width" in body
    assert "originX: 0" in body


def test_pass_98_commit_clips_candidate_before_difference_and_history():
    body = _function_body("_commitAdjustment")
    clip = body.index("applyMask(")
    no_op = body.index("if (!changed) {")
    layer_history = body.index("_pushLayerUndo(target.layer")
    pixel_history = body.index("pushPixelUndo(target.undoLabel")
    assert clip < no_op < layer_history
    assert clip < no_op < pixel_history
    assert "window.SPBSelectionClip?.applyMask" in body
    assert "target.originX || 0, target.originY || 0" in body
    assert "selected pixels already match" in body


def test_pass_98_success_toasts_depend_on_real_commit():
    relevant = _span("function applyGradientMap", "// Prompt-based adjustment dialogs")
    assert "\n    _commitAdjustment(target);" not in relevant
    assert relevant.count("if (_commitAdjustment(target)") >= 9
    tail = _span("function applyVignette", "// 2026-04-18 marathon — replaced raw prompt()")
    assert "\n    _commitAdjustment(target);" not in tail
    assert tail.count("if (_commitAdjustment(target))") == 4


def test_pass_98_runtime_is_cache_busted():
    assert "spb93-adjustment-selection-boundary-20260717" in HTML
    assert "spb93-batch-filter-transactions-20260717" in HTML
