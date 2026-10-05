"""SPB-93 Pass 107 — non-round Layer tips own their softness field."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def test_square_soft_stamp_uses_square_distance_not_round_distance():
    script = r"""
const fs=require('fs');
const footprints=require('./js/canvas/brush-footprint.js');
const source=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const start=source.indexOf('function _drawLayerPixelStamp');
const end=source.indexOf('function _drawLayerNoiseStamp',start);
let stampImage=null;
const sctx={
  createImageData(w,h){return {data:new Uint8ClampedArray(w*h*4)};},
  putImageData(image){stampImage=image;},
  drawImage(){throw new Error('unexpected texture');}
};
global.document={createElement(){return {width:0,height:0,getContext(){return sctx;}};}};
const outer={drawImage(){}};
function _brushFalloff(distanceSquared,radius,hardness){return footprints.softFalloff(distanceSquared,radius,hardness);}
eval(source.slice(start,end));
_drawLayerPixelStamp(outer,10,10,2,'#ff0000',1,0,null,footprints.create('square',2));
const alpha=(x,y)=>stampImage.data[(y*5+x)*4+3];
process.stdout.write(JSON.stringify({axis:alpha(3,2),diagonal:alpha(3,3),center:alpha(2,2)}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True,
                            capture_output=True, check=True)
    data = json.loads(result.stdout)
    assert data == {"axis": 128, "diagonal": 128, "center": 255}


def test_normal_and_special_nonround_soft_stamps_route_to_shape_kernel():
    normal_start = CANVAS.index("function _paintOnLayerAt")
    normal_end = CANVAS.index("// Workstream 6", normal_start)
    normal = CANVAS[normal_start:normal_end]
    special_start = CANVAS.index("function _drawLayerSpecialStamp")
    special_end = CANVAS.index("// SPB-93 tick 5", special_start)
    special = CANVAS[special_start:special_end]
    assert "else if (footprint.shape !== 'round')" in normal
    assert "_drawLayerPixelStamp(" in normal
    assert "if (footprint.shape !== 'round')" in special
    assert "specialCanvas, footprint" in special
    assert normal.index("footprint.shape === 'noise'") < normal.index("footprint.shape !== 'round'")


def test_runtime_token_and_mirror_are_current():
    assert "spb93-recolor-layer-sample-20260717" in HTML
    assert "spb93-layer-shape-softness-20260717" in HTML
    for relative in ("paint-booth-3-canvas.js", "paint-booth-v2.html"):
        assert (ROOT / relative).read_bytes() == (ROOT / "electron-app/server" / relative).read_bytes()
