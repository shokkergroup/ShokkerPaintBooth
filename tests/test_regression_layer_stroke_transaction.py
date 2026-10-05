"""SPB-93 Pass 48: transactional Layer brush activation and interruption cleanup."""

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


def test_layer_surface_failure_is_visible_and_never_pushes_history():
    data = _node(
        r"""
const fs=require('fs');
const text=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const start=text.indexOf('function _beginLayerPixelStroke');
const end=text.indexOf('window._beginLayerPixelStroke',start);
global.window={};
const layer={id:'paint',name:'Paint'};
let ready=false,undos=0,toasts=[];
function getSelectedEditableLayer(){return layer;}
function _initLayerPaintCanvas(){return ready;}
function _diagnoseLayerPaintFail(){return 'surface offline';}
function _pushLayerUndo(target,label){undos++;}
function showToast(message,kind){toasts.push({message,kind});}
eval(text.slice(start,end));
const failed=_beginLayerPixelStroke('Smudge','smudge on layer');
ready=true;
const acquired=_beginLayerPixelStroke('Healing Brush',null);
const started=_beginLayerPixelStroke('Smudge','smudge on layer');
process.stdout.write(JSON.stringify({failed,acquired:acquired?.id,started:started?.id,undos,toasts}));
"""
    )
    assert data["failed"] is None
    assert data["acquired"] == data["started"] == "paint"
    # Pass 53 defers history until commit proves a pixel changed.
    assert data["undos"] == 0
    assert data["toasts"][0]["kind"] == "warn"
    assert data["toasts"][0]["message"].startswith("Smudge aborted")
    assert data["toasts"][0]["message"].endswith("surface offline")


def test_every_layer_only_brush_uses_the_transaction_gate_without_composite_fallback():
    start = CANVAS.index("if (canvasMode === 'clone')")
    end = CANVAS.index("// === END NEW TOOLS ===", start)
    down = CANVAS[start:end]
    assert down.count("_beginLayerPixelStroke(") == 9
    assert "pushPixelUndo(" not in down
    assert "_initLayerPaintCanvas(" not in down
    assert down.count("_pushLayerUndo(") == 0
    helper_start = CANVAS.index("function _beginLayerPixelStroke")
    helper_end = CANVAS.index("window._beginLayerPixelStroke", helper_start)
    helper = CANVAS[helper_start:helper_end]
    assert "_pendingLayerPaintUndo" in helper
    assert "_pushLayerUndo(" not in helper
    assert "!!_beginLayerPixelStroke(null, canvasMode + ' on layer')" in CANVAS


def test_pointer_cancel_finishes_brush_state_instead_of_leaking_the_layer_buffer():
    start = CANVAS.index("canvas.addEventListener('pointercancel'")
    end = CANVAS.index("}, { passive: true });", start)
    cancel = CANVAS[start:end]
    assert "_finishActiveBrushStroke()" in cancel
    lifecycle_start = CANVAS.index("function _releaseActiveBrushStrokeState")
    lifecycle_end = CANVAS.index("// All modes that show a brush cursor", lifecycle_start)
    lifecycle = CANVAS[lifecycle_start:lifecycle_end]
    assert "_commitLayerPaint()" in lifecycle
    assert "window.endHealingStroke" in lifecycle
    assert "window.SPBRecolorBrush?.endStroke" in lifecycle
    assert "_resetBrushSpacing()" in lifecycle
    assert "isDrawing = false" in lifecycle


def test_pass_48_runtime_is_cache_busted_and_mirrored():
    assert "spb93-layer-stroke-transaction-20260717" in HTML
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
