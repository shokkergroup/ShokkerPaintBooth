"""SPB-93 Pass 151: an empty Layer document stays a Layer document in the UI."""

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


def test_pass_151_empty_loaded_layer_document_does_not_invoke_smart_tga():
    source = _function_source("renderLayerPanel")
    script = r"""
const container = {innerHTML:''};
const _psdLayers = [];
let _psdLayersLoaded = true;
const paintImageData = {allocated:true};
let smartCalls = 0;
const window = {SmartSep:{renderInto(){smartCalls++;}}};
const document = {getElementById(id){return id === 'layerPanelContent' ? container : null;}};
function getComputedStyle(){return {display:'block'};}
""" + source + r"""
renderLayerPanel();
console.log(JSON.stringify({html:container.innerHTML,smartCalls}));
"""
    payload = json.loads(subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout)
    assert payload["smartCalls"] == 0
    assert "EMPTY LAYER DOCUMENT" in payload["html"]
    assert "addBlankLayer()" in payload["html"]
    assert "TGA LOADED" not in payload["html"]


def test_pass_151_flat_image_still_routes_to_smart_tga():
    source = _function_source("renderLayerPanel")
    script = r"""
const container = {innerHTML:''};
const _psdLayers = [];
let _psdLayersLoaded = false;
const paintImageData = {allocated:true};
let smartCalls = 0;
const window = {SmartSep:{renderInto(target){smartCalls++; target.innerHTML='SMART TGA';}}};
const document = {getElementById(id){return id === 'layerPanelContent' ? container : null;}};
function getComputedStyle(){return {display:'none'};}
""" + source + r"""
renderLayerPanel();
console.log(JSON.stringify({html:container.innerHTML,smartCalls}));
"""
    payload = json.loads(subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout)
    assert payload == {"html": "SMART TGA", "smartCalls": 1}


def test_pass_151_runtime_is_cache_busted():
    assert re.search(r'paint-booth-3-canvas\.js\?v=spb93-[^"\s]+', HTML)
    assert "spb93-empty-layer-panel-20260717" in HTML
    assert "spb93-layer-factory-contract-20260717" in HTML
