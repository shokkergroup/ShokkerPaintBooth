import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def test_shape_gesture_math_matches_photoshop_style_modifiers_and_rejects_noops():
    script = r"""
const s = require('./js/canvas/layer/shape-gesture.js');
const horizontal = s.resolveGesture({x:0,y:0}, {x:10,y:0}, 'line', {shiftKey:true});
const nearHorizontal = s.resolveGesture({x:0,y:0}, {x:10,y:4}, 'line', {shiftKey:true});
const square = s.resolveGesture({x:0,y:0}, {x:10,y:4}, 'rect', {shiftKey:true});
const centered = s.resolveGesture({x:5,y:5}, {x:8,y:7}, 'ellipse', {altKey:true});
const centeredSquare = s.resolveGesture({x:0,y:0}, {x:3,y:5}, 'rect', {shiftKey:true,altKey:true});
process.stdout.write(JSON.stringify({
  horizontal,
  nearHorizontal,
  square,
  centered,
  centeredSquare,
  click:s.validateGesture({x:1,y:1},{x:1,y:1},'rect',{filled:true,strokeWidth:2}),
  invisible:s.validateGesture({x:1,y:1},{x:8,y:8},'rect',{filled:false,strokeWidth:0}),
  invisibleLine:s.validateGesture({x:1,y:1},{x:8,y:8},'line',{filled:true,strokeWidth:0}),
  visible:s.validateGesture({x:1,y:1},{x:8,y:8},'rect',{filled:false,strokeWidth:2}),
  radius:s.polygonRadius({x:0,y:0},{x:10,y:6}),
  dirty:s.dirtyRect({x:1,y:1},{x:9,y:5},10,8,2,'rect')
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data["horizontal"] == {"start": {"x": 0, "y": 0}, "end": {"x": 10, "y": 0}}
    assert abs(data["nearHorizontal"]["end"]["y"]) < 1e-9
    assert abs(data["nearHorizontal"]["end"]["x"] - (116 ** 0.5)) < 1e-9
    assert data["square"] == {"start": {"x": 0, "y": 0}, "end": {"x": 10, "y": 10}}
    assert data["centered"] == {"start": {"x": 2, "y": 3}, "end": {"x": 8, "y": 7}}
    assert data["centeredSquare"] == {"start": {"x": -5, "y": -5}, "end": {"x": 5, "y": 5}}
    assert data["click"]["valid"] is False
    assert data["invisible"]["valid"] is False
    assert data["invisibleLine"]["valid"] is False
    assert data["visible"]["valid"] is True
    assert data["radius"] == 3
    assert data["dirty"] == {"x": 0, "y": 0, "width": 10, "height": 8}


def test_shape_preview_commit_and_history_share_one_validated_gesture_contract():
    assert CANVAS.count("_startShapeGesture(pos)") >= 2
    assert CANVAS.count("_updateShapeGesture(e)") >= 2
    assert CANVAS.count("_completeShapeGesture(e)") >= 2
    assert "_shapeGestureTarget = { kind: 'layer-create' };" in CANVAS
    assert "window.SPBShapeGesture.resolveGesture" in CANVAS
    assert "function _shapeCanvasPointFromEvent(e, clamp)" in CANVAS
    assert "const pointer = _shapeCanvasPointFromEvent(e, true);" in CANVAS
    assert "canvasMode !== 'heal' && canvasMode !== 'shape'" in CANVAS
    assert "window.SPBShapeGesture.polygonRadius(startPt, endPt)" in CANVAS
    assert "_restoreShapePreviewGuide()" in CANVAS
    assert "window.SPBShapeGesture.dirtyRect(" in CANVAS

    commit = CANVAS[CANVAS.index("function commitShape"): CANVAS.index("// CLONE STAMP TOOL")]
    assert "window.SPBShapeGesture.validateGesture" in commit
    assert "return false;" in commit
    assert commit.index("window.SPBShapeGesture.validateGesture") < commit.index("_pushLayerStackUndo('add shape layer')")
    assert "return true;" in commit


def test_shape_ui_runtime_and_packaged_mirrors_are_truthful():
    assert "drag to create a new Shape layer; Shift constrains proportions or angle; Alt draws from center" in HTML
    assert "id=\"shapeFilledLabel\"" in HTML
    assert "Shape stroke width in canvas pixels (0 disables stroke)" in HTML
    assert "onchange=\"if(typeof syncShapeOptionsUI==='function')syncShapeOptionsUI();\"" in HTML
    module_tag = "js/canvas/layer/shape-gesture.js?v=spb93-shape-naturalness-v2-20260715"
    assert module_tag in HTML
    assert HTML.index(module_tag) < HTML.index("paint-booth-3-canvas.js?v=")
    assert "js/canvas/layer/shape-gesture.js" in MANIFEST["files"] if isinstance(MANIFEST, dict) else MANIFEST
    assert "Layer: New Shape layer" in CANVAS
    assert "${toolName} creates a new layer and only works in Layer Mode" in CANVAS

    for relative in (
        "paint-booth-v2.html",
        "paint-booth-3-canvas.js",
        "js/canvas/layer/shape-gesture.js",
    ):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
