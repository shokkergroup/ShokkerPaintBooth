"""SPB-93 Pass 139: whole-Layer drag honors lock in every toolbar mode."""

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


def test_pass_139_ctrl_drag_handler_has_an_unconditional_layer_lock_gate():
    start = CANVAS.index("const _spbExplicitLayerManipulation")
    end = CANVAS.index("var onLayerDragMove", start)
    routing = CANVAS[start:end]
    assert "if (selLayer.locked)" in routing
    assert "if (inLayerMode && _spbExplicitLayerManipulation && selLayer.locked)" not in routing
    assert routing.index("if (selLayer.locked)") < routing.index("startLayerDrag(selLayer")


def test_pass_139_drag_api_refuses_locked_layers_and_noop_end_skips_preview():
    source = "\n".join(_function_source(name) for name in ("startLayerDrag", "endLayerDrag"))
    script = r"""
let _layerDragState = null;
let _layerDragCompositeScheduler = null;
const events = [];
function showToast(message){events.push(['toast',message]);}
function triggerPreviewRender(){events.push(['preview']);}
function recompositeFromLayers(){}
function drawLayerBounds(){}
""" + source + r"""
const refused = startLayerDrag({id:'locked',name:'Locked Art',locked:true,bbox:[0,0,10,10]}, 1, 1);
const emptyEnd = endLayerDrag();
const started = startLayerDrag({id:'open',name:'Open Art',locked:false,bbox:[0,0,10,10]}, 1, 1);
const clickEnd = endLayerDrag();
console.log(JSON.stringify({refused,emptyEnd,started,clickEnd,events}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert payload["refused"] is False and payload["emptyEnd"] is False
    assert payload["started"] is True and payload["clickEnd"] is False
    assert not [event for event in payload["events"] if event[0] == "preview"]
    assert any("locked" in event[1].lower() for event in payload["events"] if event[0] == "toast")


def test_pass_139_real_move_refreshes_once_and_returns_true():
    source = _function_source("endLayerDrag")
    script = r"""
let _layerDragState = {didMove:true};
let _layerDragCompositeScheduler = null;
const events = [];
function showToast(message){events.push(['toast',message]);}
function triggerPreviewRender(){events.push(['preview']);}
function recompositeFromLayers(){}
function drawLayerBounds(){}
""" + source + r"""
const moved = endLayerDrag();
console.log(JSON.stringify({moved,events}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert payload["moved"] is True
    assert [event[0] for event in payload["events"]] == ["preview", "toast"]


def test_pass_139_runtime_is_cache_busted_and_mirrored():
    assert "spb93-layer-drag-lock-boundary-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
