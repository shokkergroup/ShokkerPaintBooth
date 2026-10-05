"""SPB-93 Pass 42: Layer Transform reports refusal and clears stale metadata."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _node(script: str):
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def _span(start: str, end: str) -> str:
    start_index = CANVAS.index(start)
    return CANVAS[start_index : CANVAS.index(end, start_index)]


def test_missing_and_locked_layers_refuse_and_clear_pending_metadata():
    data = _node(
        r"""
const fs=require('fs');
const text=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const start=text.indexOf('function activateLayerTransform()');
const end=text.indexOf('// Commit layer transform',start);
eval(text.slice(start,end));
var _pendingLayerTransformMeta={sessionScopeLabel:'stale'};
var currentLayer=null;
function getSelectedLayer(){return currentLayer;}
function showToast(){}
const missing=activateLayerTransform();
const missingMeta=_pendingLayerTransformMeta;
_pendingLayerTransformMeta={sessionScopeLabel:'also stale'};
currentLayer={id:'wire',name:'Wire',img:{},bbox:[0,0,10,10],locked:true};
const locked=activateLayerTransform();
process.stdout.write(JSON.stringify({missing,missingMeta,locked,lockedMeta:_pendingLayerTransformMeta}));
"""
    )
    assert data == {
        "missing": False,
        "missingMeta": None,
        "locked": False,
        "lockedMeta": None,
    }


def test_activation_success_is_propagated_and_failed_lift_metadata_is_cleared():
    activation = _span("function activateLayerTransform", "// Commit layer transform")
    selected = _span("function transformSelectedLayerRegion", "window.transformSelectedLayerRegion")
    request = _span("function requestContextTransform", "window.requestContextTransform")
    assert "return false;" in activation
    assert "return true;" in activation
    assert activation.count("_pendingLayerTransformMeta = null;") >= 3
    assert "const activated = activateLayerTransform() === true;" in selected
    assert "if (!activated)" in selected
    assert "_restoreLayerStack(sessionBeforeCapture.snapshot" in selected
    assert "_restoreZoneSourceLayers(sessionBeforeCapture.zoneSourceLayers)" in selected
    assert "undoLayerEdit" not in selected
    assert "_pendingLayerTransformMeta = null;" in selected
    assert "const editableLayer" in request
    assert "return activateLayerTransform() === true;" in request


def test_canvas_cache_token_forces_truthful_activation_runtime():
    assert "spb93-transform-activation-truth-20260716" in HTML


def test_root_and_packaged_activation_runtime_are_byte_identical():
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
