"""SPB-93 Pass 112: the shared Tolerance slider tells every engine the truth."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start_marker, end_marker):
    start = CANVAS.index(start_marker)
    return CANVAS[start : CANVAS.index(end_marker, start)]


def test_shared_tolerance_contract_preserves_zero_and_clamps_rgb_range():
    normalizer = _span(
        "function _normalizeColorTolerance",
        "function _readCanvasTolerance",
    )
    assert "Number.parseInt(value, 10)" in normalizer
    assert "Math.max(0, Math.min(255, resolved))" in normalizer
    assert "||" not in normalizer


def test_canvas_color_tools_use_the_same_tolerance_reader():
    for legacy in (
        "parseInt(document.getElementById('wandTolerance').value) || 32",
        "parseInt(document.getElementById('wandTolerance')?.value, 10) || 32",
        "parseInt(document.getElementById('wandTolerance')?.value || 32)",
    ):
        assert legacy not in CANVAS

    for tool_call in (
        "applyMagicWandSelection(pos.x, pos.y, tolerance, e)",
        "applySelectAllColorSelection(pos.x, pos.y, tolerance, e)",
        "applyEdgeRegionSelection(pos.x, pos.y, tolerance, e)",
    ):
        location = CANVAS.index(tool_call)
        assert "const tolerance = _readCanvasTolerance();" in CANVAS[location - 180 : location]

    assert CANVAS.count("_readCanvasTolerance()") >= 9


def test_both_tolerance_sliders_expose_exact_match_endpoint():
    assert 'id="wandTolerance" type="range" min="0" max="255"' in HTML
    dialog = _span("function _openAdjustmentColorDialog", "function openGradientMapDialog")
    assert 'type="range" min="0" max="120"' in dialog
    assert "payload.tolerance = _normalizeColorTolerance(toleranceInput.value, 40)" in dialog
    assert "config.tolerance || 40" not in dialog


def test_pass_112_runtime_token_and_mirror_are_current():
    assert "spb93-tolerance-zero-truth-20260717" in HTML
    server = ROOT / "electron-app/server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
