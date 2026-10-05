"""SPB-93 Pass 75: Pencil cannot expose or mutate ignored Hardness."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_pencil_hides_the_hardness_control_its_engine_does_not_read():
    assert "const showBrushHardness = showBrush && mode !== 'pencil'" in CANVAS
    for control_id in ("brushHardnessLabel", "brushHardness", "brushHardnessVal"):
        assert f"getElementById('{control_id}').style.display = showBrushHardness ? '' : 'none'" in CANVAS

    start = CANVAS.index("function paintPencil")
    pencil = CANVAS[start : CANVAS.index("window.paintPencil", start)]
    assert "brushHardness" not in pencil
    assert "_createBrushFootprint(radius)" in pencil


def test_hidden_hardness_shortcuts_do_not_change_the_next_brush_while_penciling():
    helper_start = CANVAS.index("function _activeToolConsumesHardnessShortcut")
    helper = CANVAS[helper_start : CANVAS.index("document.addEventListener('keydown'", helper_start)]
    assert "'pencil'" not in helper
    shortcut_start = CANVAS.index("// Brush hardness: { and } keys")
    shortcuts = CANVAS[shortcut_start : CANVAS.index("document.addEventListener('keyup'", shortcut_start)]
    assert shortcuts.count("_activeToolConsumesHardnessShortcut()") == 2


def test_internal_pencil_documentation_matches_secondary_button_contract():
    assert "Hard-edged, size-controlled editing (Photoshop-style Pencil)" in CANVAS
    assert "X swaps foreground/background" in CANVAS
    assert "Left-click paints FG color, right-click paints BG color" not in CANVAS


def test_pass_75_runtime_is_cache_busted_and_mirrored():
    assert "spb93-pencil-hardness-truth-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
