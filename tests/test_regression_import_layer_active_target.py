"""SPB-93 Pass 136: + Layer imports one complete, selected Layer transaction."""

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


def test_pass_136_import_commit_is_single_history_and_selects_the_new_layer():
    source = _function_source("addLayerFromFile")
    assert source.count("_pushLayerStackUndo('add layer from file')") == 1
    assert source.index("_pushLayerStackUndo('add layer from file')") < source.index("_psdLayers.push(newLayer)")
    assert source.index("_psdLayers.push(newLayer)") < source.index("selectPSDLayer(newLayer.id)")
    assert "img.onerror = function" in source and "reader.onerror = function" in source
    for field in ("blendMode: 'source-over'", "locked: false", "alphaLock: false", "clippingMask: false"):
        assert field in source


def test_pass_136_small_image_import_is_functional_and_activates_its_layer():
    source = _function_source("addLayerFromFile")
    script = r"""
const events = [];
const _psdLayers = [{id:'old'}];
let _psdLayersLoaded = true;
const input = {files:[{name:'door-logo.png'}],click(){this.onchange();}};
const paintCanvas = {width:100,height:80};
function makeCanvas(){return {width:0,height:0,getContext(){return {drawImage(){}};}};}
const document = {
  createElement(tag){return tag === 'input' ? input : makeCanvas();},
  getElementById(id){return id === 'paintCanvas' ? paintCanvas : null;}
};
class FileReader {
  readAsDataURL(){this.onload({target:{result:'data:image/png;base64,AA'}});}
}
class Image {
  constructor(){this.naturalWidth=20;this.naturalHeight=10;}
  set src(_value){this.onload();}
}
function _pushLayerStackUndo(label){events.push(['history',label]);}
function recompositeFromLayers(){events.push(['composite']);}
function selectPSDLayer(id){events.push(['select',id]);}
function triggerPreviewRender(){events.push(['preview']);}
function showToast(message){events.push(['toast',message]);}
""" + source + r"""
addLayerFromFile();
const added = _psdLayers[1];
console.log(JSON.stringify({
  count:_psdLayers.length,
  name:added.name,
  bbox:added.bbox,
  defaults:[added.blendMode,added.locked,added.alphaLock,added.clippingMask],
  events
}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert payload["count"] == 2 and payload["name"] == "door-logo"
    assert payload["bbox"] == [40, 35, 60, 45]
    assert payload["defaults"] == ["source-over", False, False, False]
    assert [event[0] for event in payload["events"]].count("history") == 1
    assert any(event[0] == "select" and event[1].startswith("psd_added_") for event in payload["events"])


def test_pass_136_runtime_is_cache_busted_and_mirrored():
    assert "spb93-import-layer-active-target-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
