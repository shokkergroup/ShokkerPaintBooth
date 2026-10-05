"""SPB-93 Pass 155: Layer via Cut is an atomic sponsor-splitting workflow."""

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
STATE = (ROOT / "paint-booth-2-state-zones.js").read_text(encoding="utf-8")
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


def test_pass_155_source_clear_and_child_insert_share_one_stack_undo():
    source = _function_source("newLayerViaCut")
    script = r"""
const events = [];
const originalImage = {kind:'original'};
const candidateImage = {kind:'candidate'};
const sourceLayer = {id:'numbers',name:'Door Numbers',img:originalImage,visible:true,locked:false,alphaLock:false};
const data = {sourceTarget:'layer',sourceLayerId:'numbers',selectionInfo:{kind:'selection'}};
const child = {id:'child',name:'Door Numbers cut'};
function isLayerToolbarMode(){return true;}
function getSelectedLayer(){return sourceLayer;}
function _captureSelectionClipboardData(){events.push(['capture']);return data;}
function _clearSelectionFromLayer(layer,selection,options){
  events.push(['candidate',layer.img.kind,options.deferCommit]);
  return {canvas:candidateImage,cleared:7};
}
function _pushLayerStackUndo(label){events.push(['undo',label,sourceLayer.img.kind]);}
function _nextUniqueLayerName(name){return name;}
function _createLayerFromClipboardData(payload,options){
  events.push(['create',sourceLayer.img.kind,options]);
  return child;
}
function showToast(message,kind){events.push(['toast',message,kind || null]);}
""" + source + r"""
const result = newLayerViaCut();
console.log(JSON.stringify({same:result===child,sourceImage:sourceLayer.img.kind,events}));
"""
    payload = json.loads(subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout)
    assert payload["same"] is True
    assert payload["sourceImage"] == "candidate"
    assert payload["events"][2] == ["undo", "new layer via cut", "original"]
    create = payload["events"][3]
    assert create[0:2] == ["create", "candidate"]
    assert create[2]["skipUndo"] is True
    assert create[2]["insertAboveSource"] is True
    assert create[2]["name"] == "Door Numbers cut"


def test_pass_155_empty_selection_is_noop_before_history_or_layer_creation():
    source = _function_source("newLayerViaCut")
    script = r"""
const events = [];
const sourceLayer = {id:'a',name:'A',img:{},visible:true,locked:false,alphaLock:false};
function isLayerToolbarMode(){return true;}
function getSelectedLayer(){return sourceLayer;}
function _captureSelectionClipboardData(){return {sourceTarget:'layer',sourceLayerId:'a',selectionInfo:{}};}
function _clearSelectionFromLayer(){return {canvas:{},cleared:0};}
function _pushLayerStackUndo(){events.push('undo');}
function _createLayerFromClipboardData(){events.push('create');}
function showToast(message){events.push(message);}
""" + source + r"""
console.log(JSON.stringify({result:newLayerViaCut(),events}));
"""
    payload = json.loads(subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout)
    assert payload["result"] is False
    assert "undo" not in payload["events"]
    assert "create" not in payload["events"]


def test_pass_155_shortcut_context_action_and_help_are_discoverable():
    assert "e.key.toLowerCase() === 'j' && e.shiftKey" in STATE
    assert "newLayerViaCut()" in STATE
    context = _function_source("renderContextActionBar")
    assert "Layer via Copy" in context
    assert "Layer via Cut" in context
    assert "selectedLayer.locked || selectedLayer.alphaLock" in context
    assert "['Ctrl+Shift+J', 'New Layer via Cut']" in CANVAS
    assert "Ctrl+Shift+J</kbd> New Layer via Cut" in HTML


def test_pass_155_split_layer_names_are_unique_and_copy_returns_the_created_layer():
    unique = _function_source("_nextUniqueLayerName")
    assert "while (usedNames.has(base + ' ' + suffix))" in unique
    cut = _function_source("newLayerViaCut")
    copy = _function_source("newLayerViaCopy")
    assert "_nextUniqueLayerName((sourceLayer.name || 'Layer') + ' cut')" in cut
    assert "_nextUniqueLayerName('Layer via Copy')" in copy
    assert "return newLayer" in copy


def test_pass_155_runtime_is_cache_busted():
    assert re.search(r'paint-booth-3-canvas\.js\?v=spb93-[^"\s]+', HTML)
    assert "spb93-layer-via-cut-20260717" in HTML
    assert "paint-booth-2-state-zones.js?v=spb93-layer-via-cut-20260717" in HTML
    assert "spb93-clone-family-contract-20260717" in HTML
