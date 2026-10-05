"""SPB-93 Pass 92: number keys respect Eraser mode and toolbar ownership."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _number_span() -> str:
    start = CANVAS.index("else if (key >= '0' && key <= '9')")
    return CANVAS[start : CANVAS.index("// Ctrl+D = deselect zone mask", start)]


def test_block_and_clear_eraser_refuse_hidden_opacity_shortcuts():
    source = _number_span()
    guard = source.index("canvasMode === 'erase' && _getEraserMode() !== 'brush'")
    control = source.index("const controlId")
    assert guard < control
    assert "Block Eraser is always 100% opaque" in source
    assert "Clear Target is a one-click command with no opacity" in source
    assert "e.preventDefault();\n                    return;" in source


def test_layer_opacity_shortcut_requires_layer_toolbar_ownership():
    source = _number_span()
    assert "typeof isLayerToolbarMode === 'function' && isLayerToolbarMode()" in source
    assert "&& _selectedLayerId && typeof setLayerOpacity === 'function'" in source


def test_layer_fill_and_gradient_keep_their_existing_tool_opacity_route():
    source = _number_span()
    assert "const isLayerPixelOpacityTool = (canvasMode === 'fill' || canvasMode === 'gradient')" in source
    assert "&& typeof isLayerToolbarMode === 'function' && isLayerToolbarMode();" in source
    assert "isLayerPixelOpacityTool ||" in source


def test_number_shortcut_boundary_cache_token_is_live():
    assert "spb93-number-shortcut-boundary-20260717" in HTML
