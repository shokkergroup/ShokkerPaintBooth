"""SPB-93 Pass 154: duplicate and Mirror Clone preserve Layer truth."""

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


def test_pass_154_mirror_clone_keeps_hidden_state_and_mirrors_across_template_width():
    source = _function_source("mirrorCloneLayer")
    script = r"""
const events = [];
const layer = {
  id:'sponsor',name:'Sponsor',path:'Door/Sponsor',visible:false,opacity:144,
  img:{width:10,height:10},bbox:[10,5,20,15],groupName:'Door',
  blendMode:'screen',alphaLock:true,clippingMask:false,effects:{stroke:{size:2}}
};
const _psdLayers = [layer];
let _selectedLayerId = 'sponsor';
const window = {};
const ctx = {translate(){},scale(){},drawImage(){events.push(['draw']);}};
const document = {
  createElement(){return {width:0,height:0,getContext(){return ctx;}};},
  getElementById(id){return id === 'paintCanvas' ? {width:100} : null;}
};
function _pushLayerStackUndo(label){events.push(['undo',label]);}
function recompositeFromLayers(){events.push(['composite']);}
function renderLayerPanel(){events.push(['panel']);}
function drawLayerBounds(){events.push(['bounds']);}
function triggerPreviewRender(){events.push(['preview']);}
function showToast(message){events.push(['toast',message]);}
""" + source + r"""
const result = mirrorCloneLayer('sponsor');
result.effects.stroke.size = 8;
console.log(JSON.stringify({
  same:result === _psdLayers[1], visible:result.visible, bbox:result.bbox,
  alphaLock:result.alphaLock, opacity:result.opacity,
  originalEffect:layer.effects.stroke.size, events
}));
"""
    payload = json.loads(subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout)
    assert payload["same"] is True
    assert payload["visible"] is False
    assert payload["bbox"] == [80, 5, 90, 15]
    assert payload["alphaLock"] is True
    assert payload["opacity"] == 144
    assert payload["originalEffect"] == 2
    assert payload["events"][0] == ["undo", "mirror clone"]


def test_pass_154_plain_duplicate_has_safe_defaults_for_legacy_layer_metadata():
    source = _function_source("duplicateLayer")
    assert "(layer.name || 'Layer') + ' copy'" in source
    assert "(layer.path || '') + ' copy'" in source
    assert "layer.visible !== false" in source
    assert "Array.isArray(layer.bbox)" in source
    assert "layer.groupName || ''" in source
    offset_source = _function_source("duplicateLayerWithOffset")
    assert "(layer.name || 'Layer') + ' copy'" in offset_source
    assert "layer.opacity != null ? layer.opacity : 255" in offset_source
    assert "layer.groupName || ''" in offset_source


def test_pass_154_layer_panel_exposes_offset_duplicate_for_repeated_sponsors():
    panel = _function_source("renderLayerPanel")
    assert "event.shiftKey ? duplicateLayerWithOffset" in panel
    assert "Shift-click makes a +50 px offset copy for repeated sponsors/numbers" in panel


def test_pass_154_runtime_is_cache_busted():
    assert re.search(r'paint-booth-3-canvas\.js\?v=spb93-[^"\s]+', HTML)
    assert "spb93-clone-family-contract-20260717" in HTML
    assert "spb93-sponsor-outline-truth-20260717" in HTML
