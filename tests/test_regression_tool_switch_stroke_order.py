"""SPB-93 Pass 88: the outgoing brush owns its tool-switch commit."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _set_mode_span() -> str:
    start = CANVAS.index("function setCanvasMode(mode)")
    return CANVAS[start : CANVAS.index("// Toggle tool-specific controls", start)]


def test_active_stroke_finishes_before_canvas_mode_changes():
    source = _set_mode_span()
    finish = source.index("_finishActiveBrushStroke()")
    mode_write = source.index("canvasMode = mode;")
    assert finish < mode_write
    assert source.count("_finishActiveBrushStroke()") == 1


def test_tool_switch_has_a_cancel_not_leak_fallback_for_inconsistent_surfaces():
    source = _set_mode_span()
    assert "if (_activeLayerCanvas && typeof _cancelLayerPaintStroke === 'function')" in source
    assert "_cancelLayerPaintStroke();" in source
    assert source.index("_cancelLayerPaintStroke();") < source.index("canvasMode = mode;")


def test_outgoing_tool_transient_resets_happen_after_commit():
    source = _set_mode_span()
    finish = source.index("_finishActiveBrushStroke()")
    for marker in ("_cloneOffset = null", "resetHealingStroke", "SPBRecolorBrush?.endStroke", "_smudgeBuffer = null"):
        assert finish < source.index(marker)


def test_tool_switch_stroke_order_cache_token_is_live():
    assert "spb93-tool-switch-stroke-order-20260717" in HTML
