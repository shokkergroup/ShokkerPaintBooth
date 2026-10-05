"""SPB-93 Pass 134: Merge Visible preserves the active base and hidden stack."""

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "js" / "canvas" / "layer" / "merge-visible.js"
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start, depth, index = match.end(), 1, match.end()
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[start : index - 1]


def test_pass_134_planner_uses_selected_visible_base_and_preserves_hidden_entries():
    script = r"""
const api = require('./js/canvas/layer/merge-visible.js');
const img = {};
const layers = [
  {id:'hidden-low',visible:false,img},
  {id:'paint',visible:true,img},
  {id:'hidden-clip',visible:false,img,clippingMask:true},
  {id:'decals',visible:true,img},
  {id:'shade',visible:true,img},
  {id:'hidden-top',visible:false,img}
];
const plan = api.plan(layers, 'decals');
console.log(JSON.stringify({
  base:plan.baseLayer.id,
  visible:plan.visibleLayers.map(layer => layer.id),
  release:plan.releaseClippingIds,
  pending:plan.pendingVisible.length
}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert payload == {
        "base": "decals",
        "visible": ["paint", "decals", "shade"],
        "release": ["hidden-clip"],
        "pending": 0,
    }


def test_pass_134_planner_refuses_loading_visible_layers_and_falls_back_to_top_visible_base():
    script = r"""
const api = require('./js/canvas/layer/merge-visible.js');
const img = {};
const layers = [
  {id:'one',visible:true,img},
  {id:'selected-hidden',visible:false,img},
  {id:'two',visible:true,img},
  {id:'loading',visible:true,img:null}
];
const plan = api.plan(layers, 'selected-hidden');
if (plan.baseLayer.id !== 'two') throw new Error('top visible fallback');
if (plan.pendingVisible.length !== 1 || plan.pendingVisible[0].id !== 'loading') throw new Error('loading gate');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_pass_134_merge_is_candidate_first_identity_preserving_and_transactional():
    body = _function_body("mergeVisibleLayers")
    history = body.index("_pushLayerStackUndo('merge visible')")
    assert body.index("const tmpCanvas") < history
    assert body.index("if (locked)") < history
    assert "planner.plan(_psdLayers, _selectedLayerId)" in body
    assert "zone.sourceLayer = base.id" in body
    assert "layer !== base && plan.visibleIds.has(layer.id)" in body
    assert "_psdLayers.length = 0" not in body
    assert "_selectedLayerId = base.id" in body
    assert "base.effects = null" in body and "base.clippingMask = false" in body
    assert "return true" in body


def test_pass_134_merge_keeps_hidden_layers_around_the_selected_base_at_runtime():
    function_source = "function mergeVisibleLayers() {" + _function_body("mergeVisibleLayers") + "\n}"
    script = r"""
global.window = {};
const planner = require('./js/canvas/layer/merge-visible.js');
const clipping = require('./js/canvas/layer/clipping-mask.js');
const img = {};
const hiddenLow = {id:'hidden-low',name:'Hidden Low',visible:false,img};
const paint = {id:'paint',name:'Paint',visible:true,img,opacity:255,blendMode:'source-over'};
const hiddenMid = {id:'hidden-mid',name:'Hidden Mid',visible:false,img};
const decals = {id:'decals',name:'Decals',visible:true,img,opacity:200,blendMode:'multiply',effects:{enabled:true}};
const shade = {id:'shade',name:'Shade',visible:true,img,opacity:255,blendMode:'screen'};
const hiddenTop = {id:'hidden-top',name:'Hidden Top',visible:false,img};
const _psdLayers = [hiddenLow, paint, hiddenMid, decals, shade, hiddenTop];
let _selectedLayerId = 'decals';
const zones = [{sourceLayer:'paint'}, {sourceLayer:'shade'}, {sourceLayer:'hidden-low'}];
const events = [];
const tmpCtx = {globalAlpha:1,globalCompositeOperation:'source-over'};
const tmpCanvas = {getContext(){return tmpCtx;}};
const paintCanvas = {width:100,height:80};
const document = {
  getElementById(id){return id === 'paintCanvas' ? paintCanvas : null;},
  createElement(){return tmpCanvas;}
};
window.SPBLayerMergeVisible = planner;
window.SPBLayerClippingMask = clipping;
function _layerAtIndexCanComposite(){return true;}
function _drawLayerPixelContent(_ctx,layers,index){events.push(['draw',layers[index].id]);return true;}
function renderLayerEffects(_ctx,layer,phase){events.push(['fx',layer.id,phase]);}
function _pushLayerStackUndo(label){events.push(['history',label,_psdLayers.map(layer=>layer.id)]);}
function recompositeFromLayers(){events.push(['composite']);}
function renderLayerPanel(){events.push(['panel']);}
function triggerPreviewRender(){events.push(['preview']);}
function showToast(message){events.push(['toast',message]);}
""" + function_source + r"""
const ok = mergeVisibleLayers();
console.log(JSON.stringify({
  ok,
  ids:_psdLayers.map(layer=>layer.id),
  selected:_selectedLayerId,
  zoneSources:zones.map(zone=>zone.sourceLayer),
  baseSame:_psdLayers[2] === decals,
  baseState:{opacity:decals.opacity,blend:decals.blendMode,effects:decals.effects,bbox:decals.bbox},
  history:events.filter(event=>event[0]==='history'),
  draws:events.filter(event=>event[0]==='draw').map(event=>event[1])
}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["ids"] == ["hidden-low", "hidden-mid", "decals", "hidden-top"]
    assert payload["selected"] == "decals" and payload["baseSame"] is True
    assert payload["zoneSources"] == ["decals", "decals", "hidden-low"]
    assert payload["baseState"] == {"opacity": 255, "blend": "source-over", "effects": None, "bbox": [0, 0, 100, 80]}
    assert len(payload["history"]) == 1
    assert payload["draws"] == ["paint", "decals", "shade"]


def test_pass_134_runtime_module_is_ordered_cache_busted_manifested_and_mirrored():
    module_tag = "js/canvas/layer/merge-visible.js?v=spb93-merge-visible-base-20260717"
    canvas_tag = "paint-booth-3-canvas.js?v="
    assert module_tag in HTML and "spb93-merge-visible-base-20260717" in HTML
    assert HTML.index(module_tag) < HTML.index(canvas_tag)
    manifest = (ROOT / "scripts" / "runtime-sync-manifest.json").read_text(encoding="utf-8")
    assert '"js/canvas/layer/merge-visible.js"' in manifest
    server = ROOT / "electron-app" / "server"
    for relative in ("js/canvas/layer/merge-visible.js", "paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
