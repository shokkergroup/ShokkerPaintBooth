from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _node(script: str):
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def _span(start_marker: str, end_marker: str) -> str:
    start = CANVAS.index(start_marker)
    return CANVAS[start:CANVAS.index(end_marker, start)]


def test_premultiplied_blend_runtime_keeps_transparent_edges_clean():
    data = _node(
        r"""
const fs=require('fs');
global.window={};
eval(fs.readFileSync('js/canvas/layer/rgba-blend.js','utf8'));
const blend=window.SPBRgbaBlend;
const painted=new Uint8ClampedArray([0,0,0,0]);
blend.sourceOverPixel(painted,0,255,0,0,255,0.25);
const first=Array.from(painted);
blend.sourceOverPixel(painted,0,255,0,0,255,0.25);
const built=Array.from(painted);
const transparentSource=new Uint8ClampedArray([0,80,160,255]);
blend.sourceOverPixel(transparentSource,0,255,0,255,0,1);
const skipped=Array.from(transparentSource);
const state=new Uint8ClampedArray([255,0,255,255]);
const empty=new Uint8ClampedArray([0,0,0,0]);
blend.mixPixel(state,0,empty,0,0.5);
const faded=Array.from(state);
blend.mixPixel(state,0,empty,0,1);
process.stdout.write(JSON.stringify({first,built,skipped,faded,restored:Array.from(state),version:blend.version}));
"""
    )
    assert data["first"] == [255, 0, 0, 64]
    assert data["built"] == [255, 0, 0, 112]
    assert data["skipped"] == [0, 80, 160, 255]
    assert data["faded"] == [255, 0, 255, 128]
    assert data["restored"] == [0, 0, 0, 0]
    assert "pass55" in data["version"]


def test_fill_dry_run_and_apply_share_source_over_on_transparency():
    data = _node(
        r"""
global.window={};
require('./js/canvas/layer/rgba-blend.js');
require('./js/canvas/layer/fill-bucket.js');
const pixels=new Uint8ClampedArray([0,0,0,0]);
const matches=new Uint8Array([2]);
const wouldChange=window.SPBFillBucket.wouldSolidFillChange(pixels,matches,255,0,0,0.25);
const afterDryRun=Array.from(pixels);
const didChange=window.SPBFillBucket.applySolidFill(pixels,matches,255,0,0,0.25);
process.stdout.write(JSON.stringify({wouldChange,afterDryRun,didChange,pixel:Array.from(pixels)}));
"""
    )
    assert data == {
        "wouldChange": True,
        "afterDryRun": [0, 0, 0, 0],
        "didChange": True,
        "pixel": [255, 0, 0, 64],
    }


def test_layer_pixel_brushes_share_the_alpha_safe_contract():
    clone = _span("function paintCloneStroke", "function drawCloneSourceIndicator")
    color = _span("function _paintColorBrushAt", "function paintColorBrush")
    pencil = _span("function paintPencil", "window.paintPencil")
    pattern = _span("function paintPatternBrushAt", "window.loadPatternBrush")
    history = _span("function paintHistoryBrush", "window.saveHistorySnapshot")
    for kernel in (clone, color, pencil, pattern):
        assert "SPBRgbaBlend?.sourceOverPixel" in kernel
    assert "SPBRgbaBlend?.mixPixel" in history
    assert "mixPixel(dstData, idx, sampleData, sampleIndex, alpha)" in history
    assert "const selection = _activeSelectionMask(w, h)" in history
    assert "_selectionCoverage(selection, py * w + px)" in history
    assert "falloff * opacity * selectionCoverage" in history
    special_fill = _span("function _applyBakedSpecialFloodFill", "// ── LAYER-MODE FILL")
    assert "SPBRgbaBlend?.sourceOverPixel" in special_fill


def test_pass_54_runtime_module_is_ordered_cache_busted_and_mirrored():
    module_tag = 'js/canvas/layer/rgba-blend.js?v=spb93-alpha-compositing-20260717'
    canvas_tag = 'paint-booth-3-canvas.js?v='
    assert module_tag in HTML
    assert HTML.index(module_tag) < HTML.index(canvas_tag)
    assert "spb93-alpha-compositing-20260717" in HTML[HTML.index(canvas_tag):]
    server = ROOT / "electron-app" / "server"
    for relative in (
        "paint-booth-v2.html",
        "paint-booth-3-canvas.js",
        "js/canvas/layer/rgba-blend.js",
    ):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
    assert '"js/canvas/layer/rgba-blend.js"' in (
        server / "scripts/runtime-sync-manifest.json"
    ).read_text(encoding="utf-8")
