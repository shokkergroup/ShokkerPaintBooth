import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _node(script: str):
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def test_pass_102_feathered_mask_interpolates_premultiplied_rgba():
    result = _node(
        r"""
const api = require('./js/canvas/layer/selection-clip.js');
const original = new Uint8ClampedArray([0,0,0,0, 0,0,255,255, 1,2,3,4, 5,6,7,8]);
const candidate = new Uint8ClampedArray([255,0,0,255, 255,0,0,255, 9,9,9,9, 10,20,30,40]);
const mask = new Uint8Array([128,128,0,255]);
const attenuated = api.applyMask(candidate, original, 4, 1, 0, 0, mask, 4, 1);
process.stdout.write(JSON.stringify({attenuated,pixels:Array.from({length:4},(_,i)=>Array.from(candidate.slice(i*4,i*4+4)))}));
"""
    )
    assert result["attenuated"] == 3
    assert result["pixels"][0] == [255, 0, 0, 128]
    assert result["pixels"][1] == [128, 0, 127, 255]
    assert result["pixels"][2] == [1, 2, 3, 4]
    assert result["pixels"][3] == [10, 20, 30, 40]


def test_pass_102_mask_offset_maps_patch_to_document_coordinates():
    result = _node(
        r"""
const api = require('./js/canvas/layer/selection-clip.js');
const original = new Uint8ClampedArray(2*2*4).fill(1);
const candidate = new Uint8ClampedArray(2*2*4).fill(9);
const mask = new Uint8Array(5*5);
mask[2*5+3] = 255;
api.applyMask(candidate, original, 2, 2, 2, 2, mask, 5, 5);
process.stdout.write(JSON.stringify(Array.from({length:4},(_,i)=>Array.from(candidate.slice(i*4,i*4+4)))));
"""
    )
    assert result == [[1, 1, 1, 1], [9, 9, 9, 9], [1, 1, 1, 1], [1, 1, 1, 1]]


def test_pass_102_layer_dabs_capture_only_a_local_patch():
    begin = CANVAS[CANVAS.index("function _beginLayerDabSelectionPatch") : CANVAS.index("function _finishLayerDabSelectionPatch")]
    finish = CANVAS[CANVAS.index("function _finishLayerDabSelectionPatch") : CANVAS.index("function _paintOnLayerAt")]
    assert "_activeSelectionMask(width, height)" in begin
    assert "window.SPBSelectionClip?.applyMask" in begin
    assert "getImageData(x0, y0, x1 - x0, y1 - y0)" in begin
    assert "patch.applyMask(" in finish
    assert "putImageData(candidate, patch.x, patch.y)" in finish


def test_spb93_inactive_zone_mask_is_not_a_layer_selection():
    result = _node(
        r"""
const api = require('./js/canvas/layer/selection-clip.js');
const alpha = new Uint8Array([7,7]);
const region = new Uint8Array([255,0]);
const inactive = api.resolveActiveMask({regionMask:region,expectedLength:2,layerMode:true,useRegion:false});
const active = api.resolveActiveMask({regionMask:region,expectedLength:2,layerMode:true,useRegion:true});
const zoneMode = api.resolveActiveMask({regionMask:region,expectedLength:2,layerMode:false,useRegion:false});
const alphaWins = api.resolveActiveMask({alphaLockMask:alpha,regionMask:region,expectedLength:2,layerMode:true,useRegion:false});
const wrongSize = api.resolveActiveMask({regionMask:region,expectedLength:3,layerMode:true,useRegion:true});
process.stdout.write(JSON.stringify({inactive:inactive===null,active:active===region,zoneMode:zoneMode===region,alphaWins:alphaWins===alpha,wrongSize:wrongSize===null}));
"""
    )
    assert result == {
        "inactive": True,
        "active": True,
        "zoneMode": True,
        "alphaWins": True,
        "wrongSize": True,
    }


def test_spb93_canvas_delegates_active_selection_policy():
    body = CANVAS[CANVAS.index("function _activeSelectionMask") : CANVAS.index("function paintBurn")]
    assert "window.SPBSelectionClip?.resolveActiveMask" in body
    assert "useRegion = z?.useRegion === true" in body
    assert "const layerMode = typeof isLayerToolbarMode" in body
    assert "layerMode && !useRegion" in body


def test_pass_102_brush_and_eraser_clip_before_preview():
    body = CANVAS[CANVAS.index("function _paintOnLayerAt") : CANVAS.index("// ─────────────────────────────────────────────────────────────────────────\n// Workstream 6", CANVAS.index("function _paintOnLayerAt"))]
    begin = body.index("_beginLayerDabSelectionPatch")
    draw = body.index("if (eraseMode && eraserModeId === 'block')")
    finish = body.index("_finishLayerDabSelectionPatch")
    preview = body.index("_scheduleActiveLayerCompositePreview")
    assert begin < draw < finish < preview
    assert "if (selectionPatch === false) return false" in body


def test_pass_102_runtime_tokens_are_current():
    assert "selection-clip.js?v=spb93-active-selection-truth-20260808a" in HTML
    assert re.search(r'<script\s+src="paint-booth-3-canvas\.js\?v=[^"\s]+"', HTML)
    assert "spb93-recolor-layer-sample-20260717" in HTML
    assert "spb93-layer-brush-selection-clip-20260717" in HTML
    assert "spb93-initial-tool-sync-20260717" in HTML
