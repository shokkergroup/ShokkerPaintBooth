"""SPB-93 Pass 84: all FG/BG entry paths keep toolbar state synchronized."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_foreground_setter_owns_every_visible_control_and_special_refresh():
    start = CANVAS.index("function setForegroundColor")
    end = CANVAS.index("function setBackgroundColor", start)
    source = CANVAS[start:end]
    assert "fgColorPicker" in source
    assert "fgColorSwatch" in source
    assert "fgHexInput" in source
    assert "syncLayerPaintSourceUI()" in source
    assert "warmLayerPaintSpecialCache(false)" in source
    assert "window.setForegroundColor = setForegroundColor" in CANVAS


def test_toolbar_inputs_delegate_to_the_shared_color_transaction():
    assert 'oninput="setForegroundColor(this.value)"' in HTML
    assert 'onchange="setForegroundColor(this.value)"' in HTML
    assert "setBackgroundColor(p.value)" in HTML
    assert "_foregroundColor=this.value" not in HTML
    assert "_backgroundColor=p.value" not in HTML


def test_default_colors_are_consistently_black_foreground_white_background():
    assert "var _foregroundColor = '#000000';" in CANVAS
    assert "var _backgroundColor = '#ffffff';" in CANVAS
    assert 'id="fgColorPicker" type="color" value="#000000"' in HTML
    assert 'id="fgHexInput" type="text" value="#000000"' in HTML
    assert "setBackgroundColor('#ffffff');" in CANVAS
    assert "setForegroundColor('#000000');" in CANVAS
    assert "button only — D is Dodge" in HTML


def test_all_non_initializing_foreground_assignments_are_centralized():
    assignments = [
        line.strip()
        for line in CANVAS.splitlines()
        if line.strip().startswith(("var _foregroundColor =", "_foregroundColor ="))
    ]
    assert assignments == [
        "var _foregroundColor = '#000000';",
        "_foregroundColor = color.toLowerCase();",
    ]


def test_swap_snapshots_both_colors_before_calling_either_setter():
    start = CANVAS.index("function swapForegroundBackground")
    end = CANVAS.index("function resetDefaultColors", start)
    source = CANVAS[start:end]
    fg_snapshot = source.index("const nextForeground = _backgroundColor;")
    bg_snapshot = source.index("const nextBackground = _foregroundColor;")
    first_write = source.index("setBackgroundColor(nextBackground);")
    second_write = source.index("setForegroundColor(nextForeground);")
    assert fg_snapshot < first_write
    assert bg_snapshot < first_write
    assert first_write < second_write


def test_toolbar_color_state_cache_token_is_live():
    assert "spb93-toolbar-color-state-20260717" in HTML
    assert "spb93-toolbar-color-swap-20260717" in HTML
