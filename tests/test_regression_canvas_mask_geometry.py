"""SPB-93 Pass 36: canvas geometry keeps Zone masks aligned and undo-atomic."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def run_node(script: str) -> dict:
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True
    )
    return json.loads(result.stdout)


def test_flip_rotate_and_resize_math_is_exact_for_region_and_spatial_masks():
    payload = run_node(r"""
const api=require('./js/canvas/zone/canvas-mask-geometry.js');
const mask=new Uint8Array([1,2,3,4,5,6]);
const soft=new Uint8Array([0,0,0,255]);
const zones=[{id:'z',regionMask:new Uint8Array([0,64,128,255]),spatialMask:new Uint8Array([0,1,2,0])}];
api.transformZones(zones,'resize',2,2,4,4);
process.stdout.write(JSON.stringify({
  h:Array.from(api.flipHorizontal(mask,3,2)),
  v:Array.from(api.flipVertical(mask,3,2)),
  cw:Array.from(api.rotateClockwise(mask,3,2)),
  nearest:Array.from(api.resizeNearest(new Uint8Array([1,2,3,4]),2,2,4,4)),
  bilinear:Array.from(api.resizeBilinear(soft,2,2,4,4)),
  regionLength:zones[0].regionMask.length,
  spatial:Array.from(zones[0].spatialMask)
}));
""")
    assert payload["h"] == [3, 2, 1, 6, 5, 4]
    assert payload["v"] == [4, 5, 6, 1, 2, 3]
    assert payload["cw"] == [4, 1, 5, 2, 6, 3]
    assert payload["nearest"] == [1, 1, 2, 2, 1, 1, 2, 2, 3, 3, 4, 4, 3, 3, 4, 4]
    assert payload["bilinear"][0] == 0
    assert payload["bilinear"][-1] == 255
    assert any(0 < value < 255 for value in payload["bilinear"])
    assert payload["regionLength"] == 16
    assert set(payload["spatial"]) <= {0, 1, 2}


def test_zone_mask_snapshot_restore_uses_stable_ids_and_deep_copies():
    payload = run_node(r"""
const api=require('./js/canvas/zone/canvas-mask-geometry.js');
const zones=[
  {id:'paint',regionMask:new Uint8Array([1,2]),spatialMask:new Uint8Array([0,1])},
  {id:'chrome',regionMask:new Uint8Array([3,4]),spatialMask:null}
];
const snapshot=api.captureZoneMasks(zones);
zones[0].regionMask[0]=99;
zones.splice(0,zones.length,zones[1],zones[0]);
const restored=api.restoreZoneMasks(zones,snapshot);
process.stdout.write(JSON.stringify({restored,state:Object.fromEntries(zones.map(z=>[z.id,{r:Array.from(z.regionMask),s:z.spatialMask?Array.from(z.spatialMask):null}]))}));
""")
    assert payload == {
        "restored": 2,
        "state": {
            "chrome": {"r": [3, 4], "s": None},
            "paint": {"r": [1, 2], "s": [0, 1]},
        },
    }


def test_actual_pixel_history_helpers_restore_dimensions_pixels_and_masks_both_directions():
    payload = run_node(r"""
const fs=require('fs'),vm=require('vm');
const source=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const api=require('./js/canvas/zone/canvas-mask-geometry.js');
function extract(name){
  const start=source.indexOf('function '+name+'('); if(start<0)throw new Error(name);
  let i=source.indexOf('{',start),depth=0;
  for(;i<source.length;i++){if(source[i]==='{')depth++;else if(source[i]==='}'&&--depth===0)break;}
  return source.slice(start,i+1);
}
const paintCanvas={width:2,height:3};
const regionCanvas={width:2,height:3};
const ctx2d={createImageData:(w,h)=>({width:w,height:h,data:new Uint8ClampedArray(w*h*4)}),putImageData:()=>{}};
paintCanvas.getContext=()=>ctx2d;
const sandbox={
  document:{getElementById:id=>id==='paintCanvas'?paintCanvas:(id==='regionCanvas'?regionCanvas:null)},
  paintImageData:{width:2,height:3,data:new Uint8ClampedArray(24).map((_,i)=>i)},
  zones:[{id:'body',regionMask:new Uint8Array([1,2,3,4,5,6]),spatialMask:new Uint8Array([0,1,2,0,1,2])}],
  SPBCanvasMaskGeometry:api, renderRegionOverlay:()=>{}, triggerPreviewRender:()=>{}
};
sandbox.window=sandbox;
vm.createContext(sandbox);
vm.runInContext(extract('_capturePixelHistoryEntry')+'\n'+extract('_restorePixelHistoryEntry'),sandbox);
const original=sandbox._capturePixelHistoryEntry('rotate',true);
paintCanvas.width=3;paintCanvas.height=2;regionCanvas.width=3;regionCanvas.height=2;
sandbox.paintImageData={width:3,height:2,data:new Uint8ClampedArray(24).fill(200)};
sandbox.zones[0].regionMask=new Uint8Array([4,1,5,2,6,3]);
sandbox.zones[0].spatialMask=new Uint8Array([0,0,1,1,2,2]);
const reciprocal=sandbox._capturePixelHistoryEntry('rotate',true);
const undo=sandbox._restorePixelHistoryEntry(original);
const undoState={w:paintCanvas.width,h:paintCanvas.height,p0:sandbox.paintImageData.data[0],mask:Array.from(sandbox.zones[0].regionMask)};
const redo=sandbox._restorePixelHistoryEntry(reciprocal);
const redoState={w:paintCanvas.width,h:paintCanvas.height,p0:sandbox.paintImageData.data[0],mask:Array.from(sandbox.zones[0].regionMask)};
process.stdout.write(JSON.stringify({undo,redo,undoState,redoState}));
""")
    assert payload == {
        "undo": True,
        "redo": True,
        "undoState": {"w": 2, "h": 3, "p0": 0, "mask": [1, 2, 3, 4, 5, 6]},
        "redoState": {"w": 3, "h": 2, "p0": 200, "mask": [4, 1, 5, 2, 6, 3]},
    }


def test_canvas_geometry_commands_use_one_pixel_mask_snapshot_and_never_clear_masks():
    source = read("paint-booth-3-canvas.js")
    geometry = source[source.index("function resizeCanvas("):source.index("window.rotateCanvas90 = rotateCanvas90")]
    assert geometry.count("{ includeZoneMasks: true }") == 4
    assert "_transformCanvasZoneMasks('resize'" in geometry
    assert "_transformCanvasZoneMasks('flip-h'" in geometry
    assert "_transformCanvasZoneMasks('flip-v'" in geometry
    assert "_transformCanvasZoneMasks('rotate-cw'" in geometry
    assert "zones.forEach(z => { z.regionMask = null; z.spatialMask = null; })" not in geometry
    assert "pushZoneUndo('Rotate canvas" not in geometry
    assert "entry.width" in source and "entry.height" in source
    assert "SPBCanvasMaskGeometry.restoreZoneMasks" in source


def test_full_2048_mask_rotation_stays_within_geometry_budget():
    payload = run_node(r"""
const {performance}=require('perf_hooks');
const api=require('./js/canvas/zone/canvas-mask-geometry.js');
const mask=new Uint8Array(2048*2048);for(let i=0;i<mask.length;i+=3)mask[i]=255;
const t=performance.now();const out=api.rotateClockwise(mask,2048,2048);
process.stdout.write(JSON.stringify({ms:performance.now()-t,length:out.length,selected:out[0]}));
""")
    assert payload["length"] == 2048 * 2048
    assert payload["ms"] < 750


def test_module_load_and_sync_contract_are_shipping_complete():
    module = "js/canvas/zone/canvas-mask-geometry.js"
    html = read("paint-booth-v2.html")
    manifest = json.loads(read("scripts/runtime-sync-manifest.json"))["files"]
    assert html.index(module) < html.index("paint-booth-3-canvas.js")
    assert module in manifest

