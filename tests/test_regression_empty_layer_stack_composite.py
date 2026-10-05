"""SPB-93 Pass 148: an empty loaded Layer stack clears stale canvas pixels."""

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


def test_pass_148_empty_loaded_stack_clears_and_refreshes_sampling_surface():
    source = _function_source("recompositeFromLayers")
    script = r"""
let _psdLayersLoaded = true;
const _psdLayers = [];
let paintImageData = {stale:true};
const events = [];
const ctx = {
  globalAlpha: 9, globalCompositeOperation: 'stale',
  clearRect(...args){events.push(['clear',...args]);},
  getImageData(...args){events.push(['read',...args]); return {fresh:true};}
};
const document = {getElementById(id){return id === 'paintCanvas' ? {width:8,height:6,getContext(){return ctx;}} : null;}};
function invalidateLayerVisibleContributionCache(){events.push(['invalidate']);}
function _layerAtIndexCanComposite(){return true;}
function renderLayerEffects(){}
function _drawLayerPixelContent(){}
""" + source + r"""
const result = recompositeFromLayers();
console.log(JSON.stringify({result,paintImageData,events,alpha:ctx.globalAlpha,op:ctx.globalCompositeOperation}));
"""
    payload = json.loads(subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True).stdout)
    assert payload["result"] is True
    assert payload["paintImageData"] == {"fresh": True}
    assert payload["events"] == [["clear", 0, 0, 8, 6], ["read", 0, 0, 8, 6], ["invalidate"]]
    assert payload["alpha"] == 1
    assert payload["op"] == "source-over"


def test_pass_148_unloaded_document_remains_a_true_noop():
    source = _function_source("recompositeFromLayers")
    assert "if (!_psdLayersLoaded) return false" in source
    assert "_psdLayers.length === 0" not in source.split("const pc =", 1)[0]


def test_pass_148_runtime_is_cache_busted():
    assert "spb93-empty-stack-composite-20260717" in HTML
    assert re.search(r'paint-booth-3-canvas\.js\?v=spb93-[^"\s]+', HTML)
    assert "spb93-shortcut-mode-boundary-20260717" in HTML
