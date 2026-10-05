from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start = match.end()
    depth = 1
    index = start
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[start : index - 1]


def test_pass_122_dynamics_sliders_are_silent_during_drag_and_report_on_commit():
    assert 'oninput="setBrushSmoothing(this.value,true)" onchange="setBrushSmoothing(this.value)"' in HTML
    assert 'oninput="setBrushStabilizer(this.value,true)" onchange="setBrushStabilizer(this.value)"' in HTML
    assert 'oninput="setBrushSmoothing(this.value);' not in HTML
    assert 'oninput="setBrushStabilizer(this.value);' not in HTML


def test_pass_122_setters_keep_control_readout_and_tooltip_synchronized():
    smoothing = _function_body("setBrushSmoothing")
    stabilizer = _function_body("setBrushStabilizer")
    for body in (smoothing, stabilizer):
        assert "setAttribute('aria-valuenow'" in body
        assert "value.textContent" in body
        assert "control.title" in body
        assert "if (!silent" in body


def test_pass_122_runtime_is_cache_busted():
    assert "spb93-dynamics-slider-commit-20260717" in HTML
    assert "spb93-brush-control-truth-20260717" in HTML
