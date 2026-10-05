"""Focused regressions for atomic multi-Layer opacity and safe Merge Selected."""

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")


def _function_source(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start, depth, index = match.start(), 0, match.start()
    while index < len(CANVAS):
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
            if depth == 0 and index > match.end():
                return CANVAS[start : index + 1]
        index += 1
    raise AssertionError(name)


def _run_node(script: str) -> dict:
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def test_multi_opacity_drag_is_one_transaction_and_cancel_restores_every_target():
    source = "\n".join(
        _function_source(name)
        for name in (
            "_syncLayerOpacityControls",
            "_layerOpacityTargetLayers",
            "_preflightLayerOpacityTargets",
            "beginLayerOpacityGesture",
            "endLayerOpacityGesture",
            "cancelLayerOpacityGesture",
            "setLayerOpacity",
        )
    )
    script = r"""
global.window = {};
const document = {querySelectorAll(){return [];}};
let _gestureCacheStamp = 0;
let _layerOpacityGesture = null;
let _selectedLayerId = 'a';
let _psdLayers = [];
const selected = new Set(['a', 'b']);
const captured = [];
const immediate = [];
const toasts = [];
let recomposites = 0;
function _spbSelectedLayerSet(){return selected;}
function _snapshotLayerStack(){return JSON.parse(JSON.stringify(_psdLayers));}
function _snapshotZoneSourceLayers(){return [{sourceLayers:['a','b']}];}
function _pushCapturedLayerStackUndo(capture,label){
  captured.push({capture,label,after:_snapshotLayerStack()}); return true;
}
function _pushLayerStackUndo(label){immediate.push({label,before:_snapshotLayerStack()});}
function _scheduleLayerOpacityRecomposite(){recomposites += 1;}
function showToast(message){toasts.push(message);}
""" + source + r"""

_psdLayers = [
  {id:'a',name:'A',opacity:255,locked:false},
  {id:'b',name:'B',opacity:128,locked:false},
  {id:'c',name:'C',opacity:32,locked:false}
];
const began = beginLayerOpacityGesture('a');
const changed = setLayerOpacity('a', 25);
const during = _psdLayers.map(layer => layer.opacity);
const historyDuring = [captured.length, immediate.length];
const ended = endLayerOpacityGesture('a');
const committed = _psdLayers.map(layer => layer.opacity);

_psdLayers = [
  {id:'a',name:'A',opacity:240,locked:false},
  {id:'b',name:'B',opacity:120,locked:false},
  {id:'c',name:'C',opacity:30,locked:false}
];
const cancelBegan = beginLayerOpacityGesture('a');
const cancelChanged = setLayerOpacity('a', 40);
const beforeCancel = _psdLayers.map(layer => layer.opacity);
const cancelled = cancelLayerOpacityGesture('a');
const afterCancel = _psdLayers.map(layer => layer.opacity);
const historyAfterCancel = [captured.length, immediate.length];

_psdLayers = [
  {id:'a',name:'A',opacity:210,locked:false},
  {id:'b',name:'Locked B',opacity:110,locked:true},
  {id:'c',name:'C',opacity:20,locked:false}
];
const lockedBegan = beginLayerOpacityGesture('a');
const lockedChanged = setLayerOpacity('a', 10);
const afterLocked = _psdLayers.map(layer => layer.opacity);

console.log(JSON.stringify({
  began,changed,during,historyDuring,ended,committed,
  captureStarts:captured[0].capture.snapshot.map(layer => layer.opacity),
  captureAfter:captured[0].after.map(layer => layer.opacity),
  captureCount:captured.length,immediateCount:immediate.length,
  cancelBegan,cancelChanged,beforeCancel,cancelled,afterCancel,historyAfterCancel,
  lockedBegan,lockedChanged,afterLocked,toasts,recomposites
}));
"""
    payload = _run_node(script)
    assert payload["began"] is True and payload["changed"] is True
    assert payload["during"] == [64, 64, 32]
    assert payload["historyDuring"] == [0, 0]
    assert payload["ended"] is True and payload["committed"] == [64, 64, 32]
    assert payload["captureStarts"] == [255, 128, 32]
    assert payload["captureAfter"] == [64, 64, 32]
    assert payload["cancelBegan"] is True and payload["cancelChanged"] is True
    assert payload["beforeCancel"] == [102, 102, 30]
    assert payload["cancelled"] is True and payload["afterCancel"] == [240, 120, 30]
    assert payload["historyAfterCancel"] == [1, 0]
    assert payload["lockedBegan"] is False and payload["lockedChanged"] is False
    assert payload["afterLocked"] == [210, 110, 20]
    assert payload["captureCount"] == 1 and payload["immediateCount"] == 0
    assert any("locked" in message.lower() and "Locked B" in message for message in payload["toasts"])


def test_multi_opacity_has_no_recursive_companion_history_and_pointer_cancel_rolls_back():
    setter = _function_source("setLayerOpacity")
    begin = _function_source("beginLayerOpacityGesture")
    cancel = _function_source("cancelLayerOpacityGesture")
    assert "setLayerOpacity._fanning" not in setter
    assert "for (const id of _sel)" not in setter
    assert "targetIds" in begin and "startOpacities" in begin
    assert "gesture.startOpacities" in cancel
    assert 'onpointercancel="cancelLayerOpacityGesture' in CANVAS


def test_merge_selected_refuses_unsafe_semantics_before_history_and_keeps_valid_merge():
    source = "\n".join(
        _function_source(name)
        for name in (
            "_spbLayerGroupBoundaryKey",
            "_layerHasEnabledMergeEffects",
            "_preflightMergeSelectedLayers",
            "mergeSelectedLayers",
        )
    )
    script = r"""
global.window = {};
let _psdLayers = [];
let _selectedLayerId = null;
let _selectedLayerIds = new Set();
const events = [];
const context = {globalAlpha:1,globalCompositeOperation:'source-over'};
const mergeCanvas = {width:0,height:0,getContext(){return context;}};
const paintCanvas = {width:80,height:60};
const document = {
  getElementById(id){return id === 'paintCanvas' ? paintCanvas : null;},
  createElement(){return mergeCanvas;}
};
const zones = [];
function _spbSelectedLayers(){return _psdLayers.filter(layer => _selectedLayerIds.has(layer.id));}
function _pushLayerStackUndo(label){events.push(['history',label,_psdLayers.map(layer=>layer.id)]);}
function _drawLayerPixelContent(_ctx,layers,index){events.push(['draw',layers[index].id]); return true;}
function _tightCropLayerCanvas(){return {canvas:{merged:true},bbox:[1,2,20,30]};}
function recompositeFromLayers(){events.push(['composite']);}
function renderLayerPanel(){events.push(['panel']);}
function triggerPreviewRender(){events.push(['preview']);}
function showToast(message,isError){events.push(['toast',message,!!isError]);}
""" + source + r"""

function layer(id, patch){return Object.assign({
  id,name:id,img:{},visible:true,locked:false,opacity:255,
  blendMode:'source-over',clippingMask:false,effects:null,
  adjHue:0,adjSat:0,adjBri:0
}, patch || {});}
function refuse(name, layers, ids){
  _psdLayers = layers;
  _selectedLayerIds = new Set(ids);
  _selectedLayerId = ids[0];
  const before = JSON.stringify(_psdLayers);
  const historyBefore = events.filter(event=>event[0]==='history').length;
  const ok = mergeSelectedLayers();
  const historyAfter = events.filter(event=>event[0]==='history').length;
  const toast = events.filter(event=>event[0]==='toast').slice(-1)[0];
  return {name,ok,unchanged:before===JSON.stringify(_psdLayers),historyDelta:historyAfter-historyBefore,toast:toast&&toast[1]};
}
const refusals = [
  refuse('contiguous',[layer('a'),layer('gap'),layer('b')],['a','b']),
  refuse('blend',[layer('a'),layer('b',{blendMode:'multiply'})],['a','b']),
  refuse('clipping',[layer('a'),layer('b',{clippingMask:true})],['a','b']),
  refuse('opacity',[layer('a'),layer('b',{opacity:200})],['a','b']),
  refuse('effects',[layer('a'),layer('b',{effects:{stroke:{enabled:true}}})],['a','b']),
  refuse('adjustments',[layer('a'),layer('b',{adjHue:5})],['a','b']),
  refuse('locked',[layer('a'),layer('b',{locked:true})],['a','b'])
];

events.length = 0;
_psdLayers = [layer('base'),layer('a'),layer('b')];
_selectedLayerIds = new Set(['a','b']);
_selectedLayerId = 'a';
const valid = mergeSelectedLayers();
console.log(JSON.stringify({
  refusals,valid,ids:_psdLayers.map(layer=>layer.id),selected:_selectedLayerId,
  history:events.filter(event=>event[0]==='history'),
  draws:events.filter(event=>event[0]==='draw').map(event=>event[1]),
  survivor:{name:_psdLayers[1].name,opacity:_psdLayers[1].opacity,
    blendMode:_psdLayers[1].blendMode,bbox:_psdLayers[1].bbox}
}));
"""
    payload = _run_node(script)
    expected_words = {
        "contiguous": "contiguous",
        "blend": "blend",
        "clipping": "clipping",
        "opacity": "opacity",
        "effects": "effect",
        "adjustments": "adjustment",
        "locked": "locked",
    }
    for refusal in payload["refusals"]:
        assert refusal["ok"] is False, refusal
        assert refusal["unchanged"] is True and refusal["historyDelta"] == 0, refusal
        assert expected_words[refusal["name"]] in refusal["toast"].lower(), refusal
    assert payload["valid"] is True
    assert payload["ids"] == ["base", "a"] and payload["selected"] == "a"
    assert len(payload["history"]) == 1
    assert payload["draws"] == ["a", "b"]
    assert payload["survivor"]["name"].startswith("a (merged ")
    assert payload["survivor"]["name"].endswith("2)")
    assert payload["survivor"]["opacity"] == 255
    assert payload["survivor"]["blendMode"] == "source-over"
    assert payload["survivor"]["bbox"] == [1, 2, 20, 30]


def test_merge_selected_preflight_dominates_history_and_canvas_mutation():
    body = _function_source("mergeSelectedLayers")
    preflight = body.index("_preflightMergeSelectedLayers(sel)")
    history = body.index("_pushLayerStackUndo('merge '")
    canvas = body.index("document.createElement('canvas')")
    assert preflight < history < canvas
