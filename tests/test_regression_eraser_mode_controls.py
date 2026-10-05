"""SPB-93 Pass 78: each Eraser mode exposes only controls it consumes."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _function(name: str, end: str) -> str:
    start = CANVAS.index(f"function {name}")
    return CANVAS[start : CANVAS.index(end, start)]


def test_eraser_mode_change_immediately_resynchronizes_options_and_cursor():
    assert 'id="eraserMode"' in HTML
    assert 'onchange="syncEraserModeControls()"' in HTML
    ui = _function("syncEraserModeControls()", "window.syncEraserModeControls")
    assert "const isBlock = mode === 'block'" in ui
    assert "const isClearTarget = mode === 'all'" in ui
    assert "['brushSizeLabel', 'brushSize', 'brushSizeVal'], !isClearTarget" in ui
    assert "['brushOpacityLabel', 'brushOpacity', 'brushOpacityVal'], !isBlock && !isClearTarget" in ui
    assert "'brushFlowVal', 'brushShape'], !isBlock && !isClearTarget" in ui
    assert "canvas.style.cursor = isClearTarget ? 'pointer' : nativeCursor" in ui
    assert "window._spbRefreshDrawZoneIndicator()" in ui
    assert "window._spbRefreshBrushCursor()" in ui
    assert "window._spbBrushNativeCursor()" in ui


def test_clear_target_has_no_footprint_ring_and_block_ring_is_square():
    cursor = _function("usesCustomBrushCursorMode(mode)", "function getBrushNativeCursor")
    assert "mode === 'erase' && _getEraserMode() === 'all'" in cursor
    visibility = _function("updateBrushCursorVisibility()", "function updateBrushCursorPosition")
    assert "const showCircle = usesCustomBrushCursorMode(canvasMode)" in visibility
    assert "canvasMode === 'erase' && _getEraserMode() === 'block'" in visibility
    assert "? 'square'" in visibility
    assert "window._spbRefreshBrushCursor = updateBrushCursorVisibility" in CANVAS


def test_eraser_indicator_explains_block_and_clear_target_semantics():
    assert "hard square eraser; Size, Spacing, Smoothing, and Stabilizer apply" in CANVAS
    assert "click once to clear the current Layer or Zone mask; brush settings do not apply" in CANVAS


def test_pass_78_runtime_is_cache_busted_and_mirrored():
    assert "spb93-eraser-mode-controls-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
