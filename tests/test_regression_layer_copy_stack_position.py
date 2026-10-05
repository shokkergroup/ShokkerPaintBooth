"""SPB-93 Pass 141: Ctrl+J/Transform Selection stay above their source Layer."""

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


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


def test_pass_141_copy_and_transform_lift_request_source_relative_insertion():
    ctrl_j = _function_source("newLayerViaCopy")
    lift = _function_source("liftSelectionToNewLayer")
    assert "insertAboveSource: true" in ctrl_j
    assert "insertAboveSource: true" in lift
    paste = _function_source("pasteAsLayer")
    assert "insertAboveSource" not in paste


def test_pass_141_creator_places_source_copies_locally_and_ordinary_paste_on_top():
    source = _function_source("_createLayerFromClipboardData")
    script = r"""
const events = [];
const _psdLayers = [{id:'bottom'},{id:'source'},{id:'cover'}];
let _psdLayersLoaded = true;
const window = {};
const document = {createElement(){return {width:0,height:0,getContext(){return {putImageData(){}};}};}};
function _pushLayerStackUndo(label){events.push(['history',label,_psdLayers.map(layer=>layer.id)]);}
function selectPSDLayer(id){events.push(['select',id]);}
function recompositeFromLayers(){events.push(['composite']);}
function renderLayerPanel(){}
function drawLayerBounds(){}
function triggerPreviewRender(){}
""" + source + r"""
const data = {width:2,height:2,imageData:{},offsetX:5,offsetY:6,sourceLayerId:'source'};
const copied = _createLayerFromClipboardData(data,{name:'Copy',idPrefix:'copy_',undoLabel:'copy',insertAboveSource:true});
const afterCopy = _psdLayers.map(layer=>layer.id);
const pasted = _createLayerFromClipboardData(data,{name:'Paste',idPrefix:'paste_',undoLabel:'paste'});
console.log(JSON.stringify({afterCopy,afterPaste:_psdLayers.map(layer=>layer.id),copied:copied.id,pasted:pasted.id,defaults:[copied.alphaLock,copied.clippingMask],events}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert payload["afterCopy"][:2] == ["bottom", "source"]
    assert payload["afterCopy"][2] == payload["copied"]
    assert payload["afterCopy"][3] == "cover"
    assert payload["afterPaste"][-1] == payload["pasted"]
    assert payload["defaults"] == [False, False]
    assert [event[1] for event in payload["events"] if event[0] == "history"] == ["copy", "paste"]


def test_pass_141_runtime_is_cache_busted_and_mirrored():
    assert "spb93-layer-copy-stack-position-20260717" in HTML
    assert re.search(r'paint-booth-3-canvas\.js\?v=spb93-[^"\s]+', HTML)
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
