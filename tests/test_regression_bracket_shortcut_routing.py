"""SPB-93 Pass 91: bracket shortcuts affect only the active consumed control."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _keyboard_span() -> str:
    start = CANVAS.index("function _nudgeActiveBrushSize")
    return CANVAS[start : CANVAS.index("document.addEventListener('keyup'", start)]


def test_spatial_brackets_route_to_spatial_size_and_other_brushes_to_brush_size():
    source = _keyboard_span()
    assert "['spatial-include', 'spatial-exclude', 'spatial-erase'].includes(canvasMode)" in source
    assert "document.getElementById('spatialBrushSize')" in source
    assert "document.getElementById('brushSize')" in source
    assert "Number(el.min)" in source
    assert "Number(el.max)" in source


def test_clear_target_has_no_size_shortcut_and_block_clear_have_no_hardness_shortcut():
    source = _keyboard_span()
    assert "const eraserIsCommand = canvasMode === 'erase' && _getEraserMode() === 'all';" in source
    assert "canvasMode === 'erase' && _getEraserMode() !== 'brush'" in source
    hardness = source[
        source.index("function _activeToolConsumesHardnessShortcut") :
        source.index("document.addEventListener('keydown'")
    ]
    assert "'pencil'" not in hardness


def test_bracket_events_are_prevented_only_when_a_control_was_changed():
    source = _keyboard_span()
    assert "if (_nudgeActiveBrushSize(-5)) e.preventDefault();" in source
    assert "if (_nudgeActiveBrushSize(5)) e.preventDefault();" in source
    assert source.count("e.preventDefault();") >= 4


def test_bracket_shortcut_routing_cache_token_is_live():
    assert "spb93-bracket-shortcut-routing-20260717" in HTML
