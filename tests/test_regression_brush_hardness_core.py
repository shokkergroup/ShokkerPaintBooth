"""SPB-93 Pass 108 — Hardness expands the solid core, then feathers."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HEALING = (ROOT / "js/canvas/layer/healing-brush.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def test_hardness_expands_full_strength_core_instead_of_shrinking_sigma():
    script = r"""
const {softFalloff}=require('./js/canvas/brush-footprint.js');
process.stdout.write(JSON.stringify({
  softMid:softFalloff(25,10,0),
  halfCore:softFalloff(25,10,0.5),
  hardMid:softFalloff(25,10,0.9),
  halfFeather:softFalloff(56.25,10,0.5),
  edge:softFalloff(100,10,0.5),
  hardEdge:softFalloff(100,10,1),
  outside:softFalloff(121,10,1)
}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True,
                            capture_output=True, check=True)
    assert json.loads(result.stdout) == {
        "softMid": 0.5,
        "halfCore": 1,
        "hardMid": 1,
        "halfFeather": 0.5,
        "edge": 0,
        "hardEdge": 1,
        "outside": 0,
    }


def test_full_brush_family_uses_one_hardness_contract():
    assert "function _brushFalloff" in CANVAS
    # Zone Brush + Clone + Color + Recolor + Smudge + Dodge/Burn + Blur +
    # Sharpen + Pattern + History + shaped Layer stamp.
    assert CANVAS.count("_brushFalloff(shapeDist2, radius, hardness)") >= 11
    assert "Math.exp(-shapeDist2" not in CANVAS
    assert "window._brushFalloff(shapeDist2, radius, hardness)" in HEALING
    assert "1.3.0-spb93-pass108-hardness-core" in HEALING


def test_round_layer_brush_keeps_full_opacity_through_the_hard_core():
    start = CANVAS.index("function _paintOnLayerAt")
    end = CANVAS.index("// Workstream 6", start)
    source = CANVAS[start:end]
    assert "_addLayerRadialFalloffStops(grad" in source
    assert "SPBBrushFootprint.radialFalloffStops(hardness, 6)" in CANVAS
    assert "opacity * 0.5" not in source


def test_runtime_modules_are_current_and_mirrored():
    assert "spb93-hardness-core-20260717" in HTML
    assert "spb93-recolor-layer-sample-20260717" in HTML
    assert "spb93-hardness-core-20260717" in HTML
    assert "healing-brush.js?v=spb93-healing-hardness-core-20260717" in HTML
    for relative in (
        "js/canvas/brush-footprint.js", "paint-booth-3-canvas.js",
        "js/canvas/layer/healing-brush.js", "paint-booth-v2.html",
    ):
        assert (ROOT / relative).read_bytes() == (ROOT / "electron-app/server" / relative).read_bytes()
