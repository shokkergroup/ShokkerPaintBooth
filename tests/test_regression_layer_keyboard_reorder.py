"""SPB-93 T40: Photoshop Layer-order shortcuts complement row dragging."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _body(name: str) -> str:
    marker = f"function {name}("
    start = CANVAS.index(marker)
    brace = CANVAS.index("{", start)
    depth = 0
    for index in range(brace, len(CANVAS)):
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
            if depth == 0:
                return CANVAS[start:index + 1]
    raise AssertionError(f"unterminated {name}")


def test_layer_order_shortcuts_are_contextual_and_do_not_resize_brushes():
    assert "e.code === 'BracketLeft' || e.code === 'BracketRight'" in CANVAS
    assert "isLayerToolbarMode() && _selectedLayerId" in CANVAS
    assert "towardTop ? moveLayerUp() : moveLayerDown()" in CANVAS
    assert "towardTop ? moveLayerToTop() : moveLayerToBottom()" in CANVAS
    assert "if (selectedLayer && !selectedLayer.locked && atBoundary)" in CANVAS
    assert "Do not overwrite it with a false boundary claim" in CANVAS
    assert "key === '[' && !e.shiftKey && !e.ctrlKey && !e.metaKey" in CANVAS
    assert "key === ']' && !e.shiftKey && !e.ctrlKey && !e.metaKey" in CANVAS


def test_send_to_edge_commands_are_locked_truthful_layer_transactions():
    top = _body("moveLayerToTop")
    bottom = _body("moveLayerToBottom")
    for body, label in ((top, "move to top"), (bottom, "move to bottom")):
        assert "if (layer.locked)" in body
        assert body.index("if (layer.locked)") < body.index(f"_pushLayerStackUndo('{label}')")
        assert "normalizeStack(_psdLayers)" in body
        assert "recompositeFromLayers()" in body
        assert "renderLayerPanel()" in body
        assert body.rstrip().endswith("return true;\n}")
        assert "zones" not in body and "regionMask" not in body
    assert "_psdLayers.push(layer)" in top
    assert "_psdLayers.unshift(layer)" in bottom


def test_layer_order_shortcuts_are_discoverable_and_packaged():
    assert "Drag or Ctrl+[ / ] to reorder" in CANVAS
    assert "Move Layer down / up" in CANVAS
    assert "Send Layer bottom / top" in CANVAS
    assert "Layer Down / Up" in HTML
    assert "Layer Bottom / Top" in HTML
    assert "paint-booth-3-canvas.js?v=spb93-tool-gauntlet-20260808" in HTML
