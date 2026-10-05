"""SPB-93 Pass 150: Layer factories share complete, unsurprising defaults."""

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


def _run_node(script: str):
    output = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout
    return json.loads(output)


def test_pass_150_offset_duplicate_preserves_zero_sign_visibility_and_editing_flags():
    source = _function_source("duplicateLayerWithOffset")
    payload = _run_node(
        r"""
const events = [];
const original = {
  id:'a', name:'Sponsor', path:'Sponsors/Sponsor', visible:false, opacity:123,
  img:{kind:'pixels'}, bbox:[10,20,110,70], groupName:'Sponsors',
  blendMode:'multiply', alphaLock:true, clippingMask:true,
  effects:{stroke:{size:4}}
};
const _psdLayers = [original];
let _selectedLayerId = 'a';
const window = {};
function _pushLayerStackUndo(label){events.push(['undo',label]);}
function recompositeFromLayers(){events.push(['composite']);}
function renderLayerPanel(){events.push(['panel']);}
function drawLayerBounds(){events.push(['bounds']);}
function triggerPreviewRender(){events.push(['preview']);}
function showToast(message){events.push(['toast',message]);}
"""
        + source
        + r"""
const result = duplicateLayerWithOffset('a', 0, -25);
result.effects.stroke.size = 9;
console.log(JSON.stringify({
  sameResult: result === _psdLayers[1],
  bbox: result.bbox, visible: result.visible, alphaLock: result.alphaLock,
  clippingMask: result.clippingMask, originalEffect: original.effects.stroke.size,
  selected: _selectedLayerId, windowSelected: window._selectedLayerId, events
}));
"""
    )
    assert payload["sameResult"] is True
    assert payload["bbox"] == [10, -5, 110, 45]
    assert payload["visible"] is False
    assert payload["alphaLock"] is True
    assert payload["clippingMask"] is True
    assert payload["originalEffect"] == 4
    assert payload["selected"] == payload["windowSelected"]
    assert payload["events"][0] == ["undo", "duplicate w/ offset"]
    assert payload["events"][-1] == ["toast", "Duplicated with offset (+0, -25)"]


def test_pass_150_blank_names_fill_the_first_gap_instead_of_repeating_after_delete():
    helper = _function_source("_nextBlankLayerName")
    payload = _run_node(
        "const _psdLayers=[{name:'Layer 1'},{name:'Decal'},{name:'Layer 3'}];\n"
        + helper
        + "\nconsole.log(JSON.stringify(_nextBlankLayerName()));"
    )
    assert payload == "Layer 2"


def test_pass_150_every_user_created_layer_has_explicit_editing_defaults():
    for function in ("onTextToolClick", "commitShape", "addLayerFromFile", "addBlankLayer"):
        source = _function_source(function)
        assert "alphaLock: false" in source, function
        assert "clippingMask: false" in source, function
        assert "effects: null" in source, function
    for function in ("duplicateLayer", "mirrorCloneLayer", "duplicateLayerWithOffset"):
        source = _function_source(function)
        assert "return newLayer" in source, function


def test_pass_150_runtime_is_cache_busted():
    assert re.search(r'paint-booth-3-canvas\.js\?v=spb93-[^"\s]+', HTML)
    assert "spb93-layer-factory-contract-20260717" in HTML
    assert "spb93-flatten-loss-confirmation-20260717" in HTML
