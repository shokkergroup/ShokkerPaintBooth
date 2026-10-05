"""SPB-93 Pass 72: secondary-button help matches the canvas input contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_right_button_remains_owned_by_context_pan_before_tool_dispatch():
    intercept = "if (spaceHeld || e.button === 1 || e.button === 2 || isPanning) return"
    assert intercept in CANVAS
    dispatch = CANVAS[CANVAS.index(intercept) : CANVAS.index("canvas.onmouseup", CANVAS.index(intercept))]
    assert "_pencilStrokeTo(pencilStart.x, pencilStart.y, false)" in dispatch
    assert "paintPencil(pencilStart.x, pencilStart.y, false)" in dispatch
    assert "if (e.button === 2) { undoLassoPoint()" not in dispatch


def test_pencil_and_lasso_explain_their_real_keyboard_workflows_once():
    user_facing = HTML + CANVAS
    assert "right=BG" not in user_facing
    assert "right-click to undo last" not in user_facing
    assert "paints FG; X swaps FG/BG" in CANVAS
    assert "press X to swap foreground/background" in HTML
    assert "Backspace removes last point" in CANVAS
    assert "Backspace removes the last point" in HTML
    backspace = CANVAS[CANVAS.index("// [55] LASSO undo last point") :]
    backspace = backspace[: backspace.index("// [56] ESCAPE")]
    assert backspace.count("showToast(") == 0


def test_pass_72_runtime_is_cache_busted_and_mirrored():
    assert "spb93-secondary-button-truth-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
