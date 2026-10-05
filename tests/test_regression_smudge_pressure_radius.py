"""SPB-93 Pass 50: Smudge pressure can expand after a light opening dab."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _node(script: str):
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def test_light_first_dab_does_not_lock_the_smudge_radius_for_the_stroke():
    data = _node(
        r"""
const fs=require('fs');
const text=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const start=text.indexOf('function paintSmudge(x, y)');
const end=text.indexOf('function _logPaintPerf',start);
global.window={_SPB_DEBUG_PAINT_PERF:false};
const controls={brushSize:{value:'2'},smudgeStrength:{value:'100'},brushFlow:{value:'100'},brushHardness:{value:'100'}};
const canvas={width:7,height:5};
global.document={getElementById(id){return id==='paintCanvas'?canvas:controls[id];}};
const data=new Uint8ClampedArray(canvas.width*canvas.height*4);
for(let y=0;y<canvas.height;y++)for(let x=0;x<canvas.width;x++){const i=(y*canvas.width+x)*4;data[i]=x*10;data[i+3]=255;}
var paintImageData={data};
var _smudgeBuffer=null,_smudgeBufferRadius=0,_smudgeBufferShape=null;
let call=0;
function _resolveBrushDynamics(){return {radius:++call===1?1:2,opacity:1};}
function _createBrushFootprint(radius){return {shape:'round',contains(dx,dy){return dx*dx+dy*dy<=radius*radius;},distanceSquared(dx,dy){return dx*dx+dy*dy;}};}
function _brushFalloff(){return 1;}
function _activeSelectionMask(){return null;}
function _selectionCoverage(mask,index){return mask?mask[index]/255:1;}
function _markActivePaintDirtyCircle(){}
function _flushPaintImageDataToCurrentSurface(){}
function _logPaintPerf(){}
eval(text.slice(start,end));
paintSmudge(2,2); // pressure radius 1, but seed capacity is configured radius 2
const before=paintImageData.data[(2*canvas.width+5)*4];
paintSmudge(3,2); // pressure rises to radius 2
const after=paintImageData.data[(2*canvas.width+5)*4];
process.stdout.write(JSON.stringify({before,after,capacity:_smudgeBufferRadius,length:_smudgeBuffer.length}));
"""
    )
    assert data == {"before": 50, "after": 40, "capacity": 2, "length": 100}


def test_smudge_uses_an_odd_centered_capacity_buffer_and_live_radius():
    start = CANVAS.index("function paintSmudge(x, y)")
    end = CANVAS.index("function _logPaintPerf", start)
    smudge = CANVAS[start:end]
    assert "Math.min(radius, bufferRadius)" in smudge
    assert "seedRadius * 2 + 1" in smudge
    assert "dy <= seedRadius" in smudge
    assert "dx <= seedRadius" in smudge
    assert "_smudgeBuffer && _smudgeBufferRadius > 0) radius = _smudgeBufferRadius" not in smudge
    assert "((dy + _smudgeBufferRadius) * bufferSide)" in smudge


def test_pass_50_runtime_is_cache_busted_and_mirrored():
    assert "spb93-smudge-pressure-radius-20260717" in HTML
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
