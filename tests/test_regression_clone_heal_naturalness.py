"""SPB-93 Pass 49: non-feedback Clone and shared-shape Healing."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HEALING_PATH = ROOT / "js/canvas/layer/healing-brush.js"
HEALING = HEALING_PATH.read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _node(script: str):
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def test_clone_reads_an_immutable_stroke_snapshot_and_respects_selection():
    data = _node(
        r"""
const fs=require('fs');
const text=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const start=text.indexOf('function paintCloneStroke(x, y)');
const end=text.indexOf('function drawCloneSourceIndicator',start);
global.window={_SPB_DEBUG_PAINT_PERF:false};
eval(fs.readFileSync('js/canvas/layer/rgba-blend.js','utf8'));
const controls={cloneOpacity:{value:'100'},brushSize:{value:'1'},brushFlow:{value:'100'},brushHardness:{value:'100'}};
const canvas={width:5,height:1,getContext(){return {}}};
global.document={getElementById(id){return id==='paintCanvas'?canvas:controls[id];}};
function make(values){const d=new Uint8ClampedArray(20); values.forEach((v,x)=>{d[x*4]=v;d[x*4+3]=255;}); return d;}
var paintImageData={data:make([10,20,30,40,50])};
var _selectedLayerId='paint';
var _cloneSource={x:0,y:0,layerId:'paint'},_cloneOffset=null,_cloneStrokeSource=new Uint8ClampedArray(paintImageData.data);
function _hasCloneSourceForActiveLayer(){return _cloneSource?.layerId===_selectedLayerId;}
function _resolveBrushDynamics(){return {radius:0,opacity:1};}
function _createBrushFootprint(){return {contains(dx,dy){return dx===0&&dy===0;},distanceSquared(dx,dy){return dx*dx+dy*dy;}};}
function _brushFalloff(){return 1;}
let selection=null;
function _activeSelectionMask(){return selection;}
function _selectionCoverage(mask,index){return mask?mask[index]/255:1;}
function _markActivePaintDirtyCircle(){}
function _flushPaintImageDataToCurrentSurface(){}
eval(text.slice(start,end));
paintCloneStroke(1,0); paintCloneStroke(2,0);
const immutable=[paintImageData.data[0],paintImageData.data[4],paintImageData.data[8]];
paintImageData={data:make([10,20,30,40,50])}; _cloneOffset=null; _cloneStrokeSource=new Uint8ClampedArray(paintImageData.data);
selection=new Uint8Array([0,255,0,0,0]);
paintCloneStroke(1,0); paintCloneStroke(2,0);
const clipped=[paintImageData.data[0],paintImageData.data[4],paintImageData.data[8]];
process.stdout.write(JSON.stringify({immutable,clipped}));
"""
    )
    assert data["immutable"] == [10, 10, 20]
    assert data["clipped"] == [10, 10, 30]


def test_clone_lifecycle_captures_and_releases_the_snapshot():
    assert "var _cloneStrokeSource = null" in CANVAS
    assert "new Uint8ClampedArray(paintImageData.data)" in CANVAS
    assert "const sourceData = _cloneStrokeSource || data" in CANVAS
    assert "const dstX = Math.round(x), dstY = Math.round(y)" in CANVAS
    assert "_selectionCoverage(selection, ty * w + tx)" in CANVAS
    assert "falloff * opacity * selectionCoverage" in CANVAS
    assert CANVAS.count("_cloneStrokeSource = null") >= 3


def test_healing_locks_and_uses_the_shared_brush_footprint():
    assert "strokeFootprintShape" in HEALING
    assert "window._createBrushFootprint(radius, strokeFootprintShape)" in HEALING
    assert "footprint.contains(dx, dy, dist2)" in HEALING
    assert "footprint.distanceSquared(dx, dy)" in HEALING
    assert "_activeSelectionMask(w, h)" in HEALING
    assert "1.3.0-spb93-pass108-hardness-core" in HEALING


def test_pass_49_runtime_is_cache_busted_and_mirrored():
    assert "spb93-clone-heal-naturalness-20260717" in HTML
    assert "healing-brush.js?v=spb93-retouch-dirty-upload-20260808a" in HTML
    assert "spb93-healing-selection-strength-20260717" in HTML
    assert "spb93-healing-footprint-20260717" in HTML
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js", "js/canvas/layer/healing-brush.js"):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
