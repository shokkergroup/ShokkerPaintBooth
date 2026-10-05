"""SPB-93 Pass 105 — Shift-click straight lines across the retouch family."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start, end):
    a = CANVAS.index(start)
    b = CANVAS.index(end, a)
    return CANVAS[a:b]


def test_opening_helper_connects_only_through_the_existing_target_pinned_anchor():
    helper = _span("function _paintOpeningWithShiftLine", "function _rememberBrushStrokeEndpoint")
    assert "event?.shiftKey ? _getBrushLineAnchor(canvasMode) : null" in helper
    assert "_forEachBrushLineDab(anchor, point, radius, paintDab)" in helper
    assert "_rememberBrushStrokeEndpoint(point.x, point.y, canvasMode)" in helper
    anchor = _span("function _getBrushLineAnchor", "function _forEachBrushLineDab")
    assert "_lastBrushStrokeAnchor.mode !== mode" in anchor
    assert "_lastBrushStrokeAnchor.targetKey !== targetKey" in anchor


def test_every_non_pencil_retouch_opening_routes_through_shift_line_helper():
    mouse_down = _span("canvas.onmousedown = function (e)", "canvas.onmouseup = function (e)")
    branches = (
        ("if (canvasMode === 'clone')", "if (canvasMode === 'heal')"),
        ("if (canvasMode === 'heal')", "if (canvasMode === 'pen')"),
        ("if (canvasMode === 'colorbrush')", "if (canvasMode === 'ellipse-marquee')"),
        ("if (canvasMode === 'recolor')", "if (canvasMode === 'smudge')"),
        ("if (canvasMode === 'smudge')", "if (canvasMode === 'history-brush')"),
        ("if (canvasMode === 'history-brush')", "if (canvasMode === 'pencil')"),
        ("if (canvasMode === 'dodge' || canvasMode === 'burn')", "if (canvasMode === 'blur-brush'"),
        ("if (canvasMode === 'blur-brush' || canvasMode === 'sharpen-brush')", "// === END NEW TOOLS ==="),
    )
    for start, end in branches:
        a = mouse_down.index(start)
        b = mouse_down.index(end, a)
        assert "_paintOpeningWithShiftLine(" in mouse_down[a:b], start
    assert "const healingOrigin = healingAnchor || healingStart" in mouse_down
    assert "window.beginHealingStroke(healingOrigin.x, healingOrigin.y)" in mouse_down


def test_pencil_seeds_prior_endpoint_and_all_drag_routes_record_the_endpoint():
    mouse_down = _span("canvas.onmousedown = function (e)", "canvas.onmouseup = function (e)")
    pencil = mouse_down[mouse_down.index("if (canvasMode === 'pencil')"):]
    assert "const pencilAnchor = e.shiftKey ? _getBrushLineAnchor(canvasMode) : null" in pencil[:2400]
    assert "_pencilStrokeTo(pencilAnchor.x, pencilAnchor.y, false)" in pencil[:2400]
    move = _span("canvas.onmousemove = function (e)", "canvas.onmousedown = function (e)")
    assert "_rememberBrushStrokeEndpoint(pppos.x, pppos.y, canvasMode)" in move
    continuous = _span("function _forEachContinuousBrushDab", "function _resetBrushSpacing")
    assert continuous.count("_rememberBrushStrokeEndpoint(x, y, canvasMode)") == 3


def test_stroke_finish_commits_anchor_for_the_whole_paint_family():
    finish = _span("function _finishActiveBrushStroke", "function _cancelActiveLayerBrushStroke")
    assert "if (typeof _commitBrushStrokeAnchor === 'function')" in finish
    assert "canvasMode === 'brush' || canvasMode === 'erase'" in finish
    assert finish.index("_commitBrushStrokeAnchor()") < finish.index("_releaseActiveBrushStrokeState()")


def test_runtime_token_and_mirror_are_current():
    assert "spb93-recolor-layer-sample-20260717" in HTML
    assert "spb93-retouch-shift-line-20260717" in HTML
    for relative in ("paint-booth-3-canvas.js", "paint-booth-v2.html"):
        assert (ROOT / relative).read_bytes() == (ROOT / "electron-app" / "server" / relative).read_bytes()
