"""SPB-93 Pass 82: Color Brush exposes only Solid/Pattern sources it consumes."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_baked_special_source_controls_are_limited_to_real_consumers():
    expected = "layerToolbarActive && (mode === 'fill' || mode === 'brush')"
    assert CANVAS.count(expected) == 2
    assert "mode === 'fill' || mode === 'brush' || mode === 'colorbrush'" not in CANVAS
    assert 'title="Layer Brush / Fill paint source"' in HTML


def test_color_brush_pattern_selector_cannot_be_hidden_by_unrelated_special_state():
    assert "patBrushEl.style.display = mode === 'colorbrush' ? '' : 'none'" in CANVAS
    refresh_start = CANVAS.index("function refreshToolbarModeSensitiveUi")
    refresh = CANVAS[refresh_start : CANVAS.index("window.refreshToolbarModeSensitiveUi", refresh_start)]
    assert "if (patBrushEl && mode === 'colorbrush')" in refresh
    assert "patBrushEl.style.display = ''" in refresh
    assert "isLayerPaintSourceSpecial()" not in refresh


def test_toolbar_describes_solid_or_pattern_instead_of_unimplemented_special_source():
    assert "paint solid RGB or the selected Pattern Brush onto the selected Layer" in HTML


def test_pass_82_runtime_is_cache_busted_and_mirrored():
    assert "spb93-colorbrush-source-truth-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
