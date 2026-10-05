"""SPB-93 Pass 51: one cleanup contract for every brush-stroke exit."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _lifecycle() -> str:
    start = CANVAS.index("function _releaseActiveBrushStrokeState")
    return CANVAS[start : CANVAS.index("// All modes that show a brush cursor", start)]


def test_mouseup_pointer_cancel_and_tool_switch_share_one_finish_path():
    assert CANVAS.count("_finishActiveBrushStroke()") >= 4  # declaration + three exit paths
    mouseup = CANVAS[CANVAS.index("canvas.onmouseup = function") : CANVAS.index("canvas.onclick = null")]
    pointer_cancel = CANVAS[
        CANVAS.index("canvas.addEventListener('pointercancel'") : CANVAS.index("canvas._spbPointerInstalled = true")
    ]
    tool_switch = CANVAS[CANVAS.index("function setCanvasMode(mode)") : CANVAS.index("// Toggle tool-specific controls")]
    assert "_finishActiveBrushStroke()" in mouseup
    assert "_finishActiveBrushStroke()" in pointer_cancel
    assert "_finishActiveBrushStroke()" in tool_switch


def test_finish_path_clears_every_stateful_brush_family_member():
    lifecycle = _lifecycle()
    for required in (
        "window.endHealingStroke",
        "window.SPBRecolorBrush?.endStroke",
        "_cloneStrokeSource = null",
        "_commitLayerPaint()",
        "_commitBrushStrokeAnchor()",
        "resetSmudge()",
        "_resetPencilStroke()",
        "_resetBrushSpacing()",
        "window.resetBrushSmoothing",
        "window.resetBrushStabilizer",
        "window._spbStrokeSymmetryMode = null",
        "isDrawing = false",
    ):
        assert required in lifecycle


def test_pencil_gets_the_same_truthful_footprint_cursor_as_other_size_tools():
    cursor_start = CANVAS.index("const BRUSH_CURSOR_MODES")
    cursor_end = CANVAS.index("let _lastBrushCursorPointer", cursor_start)
    assert "'pencil'" in CANVAS[cursor_start:cursor_end]
    # Pass 78 adds an Eraser Block override, but every other brush-family tool
    # (including Pencil) still consumes the shared brushShape fallback.
    assert ": (document.getElementById('brushShape')?.value || 'round');" in CANVAS


def test_pass_51_runtime_is_cache_busted_and_mirrored():
    assert "spb93-brush-stroke-lifecycle-20260717" in HTML
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
