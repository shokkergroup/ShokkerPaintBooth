"""SPB-93 Pass 79: Rectangle does not expose the color Tolerance it ignores."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_tolerance_visibility_matches_only_engines_that_read_color_distance():
    start = CANVAS.index("const showTolerance =")
    expression = CANVAS[start : CANVAS.index("const showSpatial", start)]
    for mode in ("wand", "selectall", "edge", "fill", "recolor"):
        assert f"mode === '{mode}'" in expression
    assert "mode === 'rect'" not in expression
    for control_id in ("wandToleranceLabel", "wandTolerance", "wandTolVal"):
        assert f"getElementById('{control_id}').style.display = showTolerance ? '' : 'none'" in CANVAS


def test_rectangle_still_exposes_selection_clear_without_borrowing_tolerance_state():
    assert "showTolerance || mode === 'brush' || mode === 'rect' || mode === 'lasso'" in CANVAS
    assert "drag a Zone selection; Shift square, Alt from center, Esc cancel" in CANVAS


def test_pass_79_runtime_is_cache_busted_and_mirrored():
    assert "spb93-rect-tolerance-truth-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
