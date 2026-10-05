"""SPB-93 Pass 157: non-clipboard operations preserve copied artwork."""

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


def test_pass_157_layer_via_copy_leaves_existing_clipboard_untouched():
    source = _function_source("newLayerViaCopy")
    script = r"""
let _clipboardData = {id:'saved-logo'};
const captured = {id:'selection'};
const created = {id:'copy-layer'};
const events = [];
function _captureSelectionClipboardData(){events.push('capture');return captured;}
function _nextUniqueLayerName(name){return name;}
function _createLayerFromClipboardData(data,options){events.push(['create',data.id,options]);return created;}
function showToast(message){events.push(['toast',message]);}
""" + source + r"""
const result = newLayerViaCopy();
console.log(JSON.stringify({same:result===created,clipboard:_clipboardData,events}));
"""
    payload = json.loads(subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout)
    assert payload["same"] is True
    assert payload["clipboard"] == {"id": "saved-logo"}
    assert payload["events"][0] == "capture"
    assert payload["events"][1][0:2] == ["create", "selection"]


def test_pass_157_transform_lift_also_captures_without_storing():
    source = _function_source("liftSelectionToNewLayer")
    assert "_captureSelectionClipboardData()" in source
    assert "_storeClipboardFromSelection" not in source
    via_copy = _function_source("newLayerViaCopy")
    assert "_captureSelectionClipboardData()" in via_copy
    assert "_storeClipboardFromSelection" not in via_copy
    cut = _function_source("cutSelection")
    assert "_storeClipboardFromSelection(true)" in cut


def test_pass_157_runtime_is_cache_busted():
    assert re.search(r'paint-booth-3-canvas\.js\?v=[^"\s]+', HTML)
    runtime = (ROOT / "electron-app/server/paint-booth-v2.html").read_text(encoding="utf-8")
    assert re.search(r'paint-booth-3-canvas\.js\?v=[^"\s]+', HTML).group() in runtime
    assert "spb93-shortcut-fallback-parity-20260717" in HTML
