"""SPB-93 Pass 153: sponsor OUTLINE has visible controls and truthful history."""

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


def test_pass_153_zero_width_is_noop_and_valid_outline_is_one_undo():
    source = _function_source("addLayerOutline")
    script = r"""
const events = [];
const layer = {id:'logo',name:'Logo',img:{width:2,height:1},bbox:[10,20,12,21],locked:false};
const _psdLayers = [layer];
const _foregroundColor = '#abcdef';
const ctx = {
  globalCompositeOperation:'source-over', fillStyle:'#000000',
  drawImage(){events.push(['draw']);}, fillRect(){events.push(['fill']);}
};
const document = {createElement(){return {width:0,height:0,getContext(){return ctx;}};}};
function _pushLayerUndo(target,label){events.push(['undo',target.id,label]);}
function recompositeFromLayers(){events.push(['composite']);}
function renderLayerPanel(){events.push(['panel']);}
function triggerPreviewRender(){events.push(['preview']);}
function showToast(message,kind){events.push(['toast',message,kind || null]);}
""" + source + r"""
const invalid = addLayerOutline('logo', '#123456', 0);
const valid = addLayerOutline('logo', '#123456', 1);
console.log(JSON.stringify({invalid,valid,bbox:layer.bbox,size:[layer.img.width,layer.img.height],events}));
"""
    payload = json.loads(subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout)
    assert payload["invalid"] is False
    assert payload["valid"] is True
    assert payload["bbox"] == [7, 17, 15, 24]
    assert payload["size"] == [8, 7]
    assert [event for event in payload["events"] if event[0] == "undo"] == [["undo", "logo", "add outline"]]
    assert payload["events"][-1] == ["toast", "Outline added: 1px #123456", None]


def test_t44_layer_panel_routes_outline_need_to_nondestructive_stroke_fx():
    source = _function_source("renderLayerPanel")
    assert "openLayerEffects('${l.id}', 'stroke')" in source
    assert ">STROKE FX</button>" in source
    assert "Open non-destructive Stroke in Layer Effects" in source
    assert "addLayerOutline('${l.id}'" not in source


def test_pass_153_runtime_is_cache_busted():
    assert re.search(r'paint-booth-3-canvas\.js\?v=spb93-[^"\s]+', HTML)
    assert "spb93-sponsor-outline-truth-20260717" in HTML
    assert "spb93-zone-mask-from-layer-20260717" in HTML
