"""SPB-93 Pass 114: fine tips and shortcut endpoints remain truthful."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start_marker, end_marker):
    start = CANVAS.index(start_marker)
    return CANVAS[start : CANVAS.index(end_marker, start)]


def test_brush_and_pencil_size_control_can_reach_its_fine_endpoint():
    assert 'id="brushSize" name="brushSize" type="range" min="1" max="300"' in HTML
    nudge = _span("function _nudgeActiveBrushSize", "function _activeToolConsumesHardnessShortcut")
    assert "'pencil'" in nudge
    assert "const min = Number(el.min) || 1" in nudge


def test_size_helpers_respect_the_visible_range_and_report_applied_value():
    bump = _span("window.bumpBrushSize", "// [07] BRUSH HARDNESS")
    assert bump.count("Number.isFinite(parsed) ? parsed : 20") == 2
    assert bump.count("Number.isFinite(Number(el.min)) ? Number(el.min) : 1") == 2
    assert bump.count("Number.isFinite(Number(el.max)) ? Number(el.max) : 300") == 2
    assert "Math.min(500" not in bump
    assert bump.count("'Brush size: ' + el.value + 'px'") == 2


def test_zero_hardness_nudges_from_zero_instead_of_jumping_to_full():
    hardness = _span("window.bumpBrushHardness", "// [08]")
    assert "Number.isFinite(parsed) ? parsed : 100" in hardness
    assert "parseInt(el.value, 10) || 100" not in hardness


def test_pass_114_runtime_token_and_mirror_are_current():
    assert "spb93-fine-size-shortcut-truth-20260717" in HTML
    server = ROOT / "electron-app/server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
