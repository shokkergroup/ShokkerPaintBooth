"""SPB-93 Pass 76: FG/BG controls appear only for color-consuming tools."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _show_color_expression() -> str:
    start = CANVAS.index("function _toolConsumesForegroundControls")
    return CANVAS[start : CANVAS.index("function refreshToolbarModeSensitiveUi", start)]


def test_pencil_exposes_the_foreground_background_controls_it_consumes():
    expression = _show_color_expression()
    assert "mode === 'pencil'" in expression
    pencil_start = CANVAS.index("function paintPencil")
    pencil = CANVAS[pencil_start : CANVAS.index("window.paintPencil", pencil_start)]
    assert "_foregroundColor" in pencil
    assert "_backgroundColor" in pencil


def test_smudge_and_eraser_do_not_show_dead_color_controls():
    expression = _show_color_expression()
    assert "mode === 'smudge'" not in expression
    assert "mode === 'erase'" not in expression
    assert CANVAS.count("const showColorBrush = _toolConsumesForegroundControls(mode, layerToolbarActive)") == 2
    assert CANVAS.count("colorBrushOpts.style.display = showColorBrush ? 'inline-flex' : 'none'") == 2


def test_pass_76_runtime_is_cache_busted_and_mirrored():
    assert "spb93-color-control-parity-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
