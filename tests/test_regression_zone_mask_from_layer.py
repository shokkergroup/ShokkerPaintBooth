"""SPB-93 Pass 152: Zone Mask from Layer is one truthful candidate transaction."""

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


def test_pass_152_identical_mask_is_noop_and_changed_mask_is_one_undo():
    source = _function_source("selectLayerPixels")
    script = r"""
const events = [];
const layer = {id:'decal',name:'Door Number',img:{width:3,height:1},bbox:[0,0,3,1]};
const _psdLayers = [layer];
const zone = {regionMask:new Uint8Array([0,255,0])};
const zones = [zone];
const selectedZoneIndex = 0;
const rgba = new Uint8ClampedArray([0,0,0,0, 0,0,0,120, 0,0,0,0]);
const ctx = {
  drawImage(...args){events.push(['draw',args.length]);},
  getImageData(){return {data:rgba};}
};
const canvas = {width:0,height:0,getContext(){return ctx;}};
const paintCanvas = {width:3,height:1};
const document = {
  getElementById(id){return id === 'paintCanvas' ? paintCanvas : null;},
  createElement(tag){return canvas;}
};
function pushUndo(index){events.push(['undo',index]);}
function renderRegionOverlay(){events.push(['overlay']);}
function triggerPreviewRender(){events.push(['preview']);}
function showToast(message,kind){events.push(['toast',message,kind || null]);}
""" + source + r"""
const first = selectLayerPixels('decal');
zone.regionMask = new Uint8Array([255,0,255]);
const second = selectLayerPixels('decal');
console.log(JSON.stringify({first,second,mask:Array.from(zone.regionMask),events}));
"""
    payload = json.loads(subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout)
    assert payload["first"] is False
    assert payload["second"] is True
    assert payload["mask"] == [0, 255, 0]
    assert [event for event in payload["events"] if event[0] == "undo"] == [["undo", 0]]
    assert [event for event in payload["events"] if event[0] == "overlay"] == [["overlay"]]
    assert [event for event in payload["events"] if event[0] == "preview"] == [["preview"]]
    assert [event for event in payload["events"] if event[0] == "draw"] == [["draw", 5], ["draw", 5]]


def test_pass_152_runtime_is_cache_busted():
    assert re.search(r'paint-booth-3-canvas\.js\?v=spb93-[^"\s]+', HTML)
    assert "spb93-zone-mask-from-layer-20260717" in HTML
    assert "spb93-empty-layer-panel-20260717" in HTML
