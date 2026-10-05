import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "js" / "canvas" / "layer" / "selection-placement.js"
HTML = ROOT / "paint-booth-v2.html"
CANVAS = ROOT / "paint-booth-3-canvas.js"
MANIFEST = ROOT / "scripts" / "runtime-sync-manifest.json"


def run_node(expression: str):
    script = f"""
const placement = require({json.dumps(str(MODULE))});
const result = {expression};
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_fit_plan_preserves_aspect_and_centers_inside_zone_selection():
    plan = run_node(
        "placement.planFit([0, 0, 400, 200], [100, 50, 300, 350], "
        "{paddingRatio: 0.10})"
    )
    assert plan["width"] == 160
    assert plan["height"] == 80
    assert plan["centerX"] == 200
    assert plan["centerY"] == 200
    assert plan["bbox"] == [120, 160, 280, 240]
    assert plan["scale"] == 0.4


def test_fit_plan_handles_reversed_rects_and_bounded_upscale():
    result = run_node(
        "({normalized: placement.normalizeRect([20, 30, 4, 10]), "
        "plan: placement.planFit([0, 0, 10, 20], [0, 0, 1000, 1000], "
        "{paddingRatio: 0, maxScale: 3})})"
    )
    assert result["normalized"] == {
        "x1": 4,
        "y1": 10,
        "x2": 20,
        "y2": 30,
        "width": 16,
        "height": 20,
    }
    assert result["plan"]["scale"] == 3
    assert result["plan"]["width"] == 30
    assert result["plan"]["height"] == 60


def test_fit_plan_rejects_empty_or_non_finite_geometry():
    result = run_node(
        "[placement.planFit([0, 0, 0, 4], [0, 0, 5, 5]), "
        "placement.planFit([0, 0, 4, 4], [0, 0, NaN, 5]), "
        "placement.normalizeRect(null)]"
    )
    assert result == [None, None, None]


def test_live_menu_replaces_unreachable_decal_state_with_safe_layer_preview():
    html = HTML.read_text(encoding="utf-8")
    canvas = CANVAS.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert "Fit Layer to Zone Selection" in html
    assert "onclick=\"fitLayerToZoneSelection()\"" in html
    assert "activateFreeTransform('decal')" not in html
    placement_tag = '<script src="js/canvas/layer/selection-placement.js'
    canvas_tag = '<script src="paint-booth-3-canvas.js'
    assert placement_tag in html
    assert html.index(placement_tag) < html.index(
        canvas_tag
    )
    assert "function fitLayerToZoneSelection()" in canvas
    fit_body = canvas.split("function fitLayerToZoneSelection()", 1)[1].split(
        "window.fitLayerToZoneSelection", 1
    )[0]
    assert "isLayerToolbarMode" in fit_body
    assert "getSelectedEditableLayer" in fit_body
    assert "_getActiveSelectionInfo" in fit_body
    assert "activateLayerTransform" in fit_body
    assert "window._spbLastPickedElementBbox = null" in fit_body
    assert "regionMask =" not in fit_body
    assert "spatialMask =" not in fit_body
    assert "js/canvas/layer/selection-placement.js" in manifest["files"]
