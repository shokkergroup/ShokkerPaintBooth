"""SPB-93 Pass 138: element transforms compose on a union Layer surface."""

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")


def test_pass_138_rotated_aabb_has_antialias_room_and_correct_orientation():
    script = r"""
const api = require('./js/canvas/layer/layer-transform-raster.js');
console.log(JSON.stringify(api.transformedAabb({centerX:20,centerY:30,width:10,height:4,rotation:90})));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    box = json.loads(result.stdout)
    assert box["width"] == 8 and box["height"] == 14
    assert box == {"x1": 16, "y1": 23, "x2": 24, "y2": 37, "width": 8, "height": 14}


def test_pass_138_union_surface_preserves_original_and_out_of_bounds_move():
    script = r"""
const api = require('./js/canvas/layer/layer-transform-raster.js');
const canvases = [];
function createCanvas(w,h){
  const canvas = {id:'canvas'+canvases.length,width:w,height:h,calls:[]};
  const ctx = {
    globalCompositeOperation:'source-over', imageSmoothingEnabled:false, imageSmoothingQuality:'low',
    save(){canvas.calls.push(['save']);}, restore(){canvas.calls.push(['restore']);},
    translate(x,y){canvas.calls.push(['translate',x,y]);}, scale(x,y){canvas.calls.push(['scale',x,y]);},
    rotate(r){canvas.calls.push(['rotate',r]);},
    clearRect(...args){canvas.calls.push(['clear',...args]);},
    drawImage(...args){canvas.calls.push(['draw',...args.map(value => value && value.id ? value.id : value)]);}
  };
  canvas.getContext = () => ctx;
  canvases.push(canvas);
  return canvas;
}
const source = {id:'source',width:100,height:50};
const item = {sourceRect:{x1:20,y1:20,x2:30,y2:30},centerX:-5,centerY:25,width:10,height:10,rotation:0};
const out = api.composeElementTransforms({source,sourceBbox:[10,10,110,60],items:[item],createCanvas});
console.log(JSON.stringify({bbox:out.bbox,width:out.canvas.width,height:out.canvas.height,canvases}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert payload["bbox"] == [-10, 10, 110, 60]
    assert payload["width"] == 120 and payload["height"] == 50
    dest_calls = payload["canvases"][0]["calls"]
    assert ["draw", "source", 0, 0, 100, 50, 20, 0, 100, 50] in dest_calls
    # Erase the extracted rectangle completely: alpha-weighted erasure leaves ghosts.
    assert ["clear", 30, 10, 10, 10] in dest_calls
    assert ["draw", "canvas1", 0, 10] in dest_calls


def test_pass_138_layer_commit_routes_master_groups_and_instances_through_union_candidate():
    assert "transformRaster?.composeElementTransforms" in CANVAS
    assert "const addTransformItem = function(rect, instanceRef)" in CANVAS
    # Single-member editing may filter siblings before adding the selected crop.
    assert re.search(r"group\.forEach\(function\(member\)\s*\{[^}]+addTransformItem\(member, null\);", CANVAS)
    assert "...window.SPBElementTransformState.item(s, rect)" in CANVAS
    assert "instances.forEach(function(instance) { addTransformItem(instance.instanceBbox, instance); })" not in CANVAS
    assert "SPBElementInstances?.relocate(layer, composed.items.map" in CANVAS
    candidate = CANVAS.index("const composed = transformRaster.composeElementTransforms")
    history = CANVAS.index("pushTransformUndoOnce();", candidate)
    mutation = CANVAS.index("layer.img = composed.canvas", candidate)
    assert candidate < history < mutation


def test_pass_138_runtime_module_is_mirrored():
    html = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
    module_tag = re.search(r'js/canvas/layer/layer-transform-raster\.js\?v=[^"\s]+', html).group(0)
    canvas_tag = "paint-booth-3-canvas.js?v="
    assert html.index(module_tag) < html.index(canvas_tag)
    relative = "js/canvas/layer/layer-transform-raster.js"
    server = ROOT / "electron-app" / "server"
    for path in (relative, "paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / path).read_bytes() == (server / path).read_bytes()
