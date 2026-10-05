"""SPB-93 Pass 44: Paste targets the selection/view; Paste in Place stays exact."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = "js/canvas/layer/clipboard-layer.js"
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _node(script: str):
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def test_auto_paste_prefers_selection_then_viewport_then_canvas_and_clamps():
    data = _node(
        r"""
const api=require('./js/canvas/layer/clipboard-layer.js');
const clip={width:40,height:20,offsetX:701,offsetY:801};
process.stdout.write(JSON.stringify({
  selection:api.resolvePastePlacement(clip,{canvasWidth:500,canvasHeight:400,selection:{minX:100,maxX:199,minY:50,maxY:149},viewportCenter:{x:20,y:20}}),
  viewport:api.resolvePastePlacement(clip,{canvasWidth:500,canvasHeight:400,viewportCenter:{x:430,y:360}}),
  canvas:api.resolvePastePlacement(clip,{canvasWidth:500,canvasHeight:400}),
  clamped:api.resolvePastePlacement({width:80,height:90},{canvasWidth:100,canvasHeight:100,viewportCenter:{x:99,y:99}}),
  inPlace:api.resolvePastePlacement(clip,{canvasWidth:500,canvasHeight:400,mode:'in-place',selection:{minX:1,maxX:3,minY:1,maxY:3}})
}));
"""
    )
    assert data["selection"] == {"x": 130, "y": 90, "reason": "selection"}
    assert data["viewport"] == {"x": 410, "y": 350, "reason": "viewport"}
    assert data["canvas"] == {"x": 230, "y": 190, "reason": "canvas"}
    assert data["clamped"] == {"x": 20, "y": 10, "reason": "viewport"}
    assert data["inPlace"] == {"x": 701, "y": 801, "reason": "in-place"}


def test_canvas_paste_uses_resolved_offsets_without_mutating_clipboard_or_linking_source():
    creator_start = CANVAS.index("function _createLayerFromClipboardData")
    creator_end = CANVAS.index("function _clearSelectionFromLayer", creator_start)
    creator = CANVAS[creator_start:creator_end]
    paste_start = CANVAS.index("function _visibleCanvasPasteCenter")
    paste_end = CANVAS.index("function applyAutoFeatherToSelection", paste_start)
    paste = CANVAS[paste_start:paste_end]
    assert "opts.offsetX" in creator and "opts.offsetY" in creator
    assert "resolvePastePlacement" in paste
    assert "selection: _getActiveSelectionInfo()" in paste
    assert "viewportCenter: _visibleCanvasPasteCenter()" in paste
    assert "offsetX: placement.x" in paste and "offsetY: placement.y" in paste
    assert "linkSourceLayer" not in paste
    assert "_clipboardData.offsetX =" not in paste


def test_paste_in_place_is_discoverable_and_has_photoshop_shortcut():
    assert "function pasteInPlace()" in CANVAS
    assert "window.pasteInPlace = pasteInPlace" in CANVAS
    assert "Ctrl+Shift+V" in CANVAS
    assert "if (typeof pasteInPlace === 'function') pasteInPlace();" in CANVAS
    assert "Paste at selection / view center" in HTML
    assert "Ctrl+Shift+V</kbd> Paste in Place" in HTML


def test_selection_aware_paste_runtime_token_and_root_mirror_contract():
    assert f"{MODULE}?v=spb93-selection-aware-paste-20260716" in HTML
    assert "spb93-selection-aware-paste-20260716" in HTML
    for relative in (MODULE, "paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
