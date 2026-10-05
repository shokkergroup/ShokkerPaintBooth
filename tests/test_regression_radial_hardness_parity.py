"""SPB-93 Pass 113: fast round stamps share the smooth hardness profile."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start_marker, end_marker):
    start = CANVAS.index(start_marker)
    return CANVAS[start : CANVAS.index(end_marker, start)]


def test_stop_table_samples_the_shared_smoothstep_curve():
    script = r"""
global.window = {};
require('./js/canvas/brush-footprint.js');
const m = window.SPBBrushFootprint;
console.log(JSON.stringify({
  stops: m.radialFalloffStops(0.5, 4),
  quarterFeather: m.softFalloff(0.625 * 0.625, 1, 0.5)
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    payload = json.loads(result.stdout)
    assert payload["stops"][0] == [0, 1]
    assert payload["stops"][1] == [0.5, 1]
    assert payload["stops"][-1] == [1, 0]
    assert abs(payload["quarterFeather"] - 0.84375) < 1e-9
    assert abs(payload["stops"][2][1] - payload["quarterFeather"]) < 1e-9


def test_round_layer_and_special_stamps_use_the_shared_stop_table():
    helper = _span(
        "function _addLayerRadialFalloffStops",
        "function _drawLayerSpecialStamp",
    )
    special = _span("function _drawLayerSpecialStamp", "// SPB-93 tick 5")
    layer = _span("function _paintOnLayerAt", "// Workstream 6 #119")
    assert "SPBBrushFootprint.radialFalloffStops(hardness, 6)" in helper
    assert "_addLayerRadialFalloffStops(grad, 255, 255, 255, opacity, hardness)" in special
    assert "_addLayerRadialFalloffStops(grad, 0, 0, 0, opacity, hardness)" in layer
    assert "_addLayerRadialFalloffStops(grad, cr, cg, cb, opacity, hardness)" in layer


def test_pass_113_tokens_and_runtime_mirrors_are_current():
    assert "brush-footprint.js?v=spb93-radial-hardness-parity-20260717" in HTML
    assert "spb93-radial-hardness-parity-20260717" in HTML
    server = ROOT / "electron-app/server"
    for relative in (
        "paint-booth-v2.html",
        "paint-booth-3-canvas.js",
        "js/canvas/brush-footprint.js",
    ):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
