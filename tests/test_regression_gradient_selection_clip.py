"""SPB-93 Pass 94: Layer Gradient clips to the active global selection."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = "js/canvas/layer/selection-clip.js"
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def _node(script: str):
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def test_offset_layer_clip_restores_every_pixel_outside_global_mask():
    data = _node(
        r"""
const api = require('./js/canvas/layer/selection-clip.js');
const original = new Uint8ClampedArray(3 * 2 * 4);
const candidate = new Uint8ClampedArray(3 * 2 * 4).fill(9);
for (let i=0;i<original.length;i+=4) original.set([1,2,3,4],i);
const mask = new Uint8Array(6 * 4);
mask[1 * 6 + 3] = 255; // global (3,1) -> local (1,0) for origin (2,1)
const restored = api.restoreOutsideMask(candidate, original, 3, 2, 2, 1, mask, 6, 4);
const pixels = [];
for (let i=0;i<candidate.length;i+=4) pixels.push(Array.from(candidate.slice(i,i+4)));
process.stdout.write(JSON.stringify({restored,pixels}));
"""
    )
    assert data["restored"] == 5
    assert data["pixels"] == [
        [1, 2, 3, 4], [9, 9, 9, 9], [1, 2, 3, 4],
        [1, 2, 3, 4], [1, 2, 3, 4], [1, 2, 3, 4],
    ]


def test_missing_mask_is_a_noop_not_an_implicit_empty_selection():
    data = _node(
        r"""
const api = require('./js/canvas/layer/selection-clip.js');
const original = new Uint8ClampedArray([1,2,3,4]);
const candidate = new Uint8ClampedArray([9,9,9,9]);
const restored = api.restoreOutsideMask(candidate, original, 1, 1, 0, 0, null, 0, 0);
process.stdout.write(JSON.stringify({restored,pixel:Array.from(candidate)}));
"""
    )
    assert data == {"restored": 0, "pixel": [9, 9, 9, 9]}


def test_layer_gradient_clips_candidate_before_difference_and_history():
    start = CANVAS.index("function fillGradientOnLayer")
    end = CANVAS.index("function _applyBakedSpecialFloodFill", start)
    source = CANVAS[start:end]
    clip = source.index("applyMask(")
    difference = source.index("SPBGradient.arraysDiffer")
    undo = source.index("_pushLayerUndo(layer, 'gradient on layer')")
    assert "_activeSelectionMask(paintCanvas.width, paintCanvas.height)" in source
    assert clip < difference < undo
    assert "window.SPBSelectionClip?.applyMask" in source


def test_selection_clip_module_is_loaded_manifested_and_mirrored():
    assert MODULE in MANIFEST["files"]
    assert 'selection-clip.js?v=spb93-active-selection-truth-20260808a' in HTML
    assert 'spb93-gradient-selection-clip-20260717' in HTML
    assert HTML.index("selection-clip.js?v=") < HTML.index("paint-booth-3-canvas.js?v=")
    assert (ROOT / MODULE).read_bytes() == (ROOT / "electron-app" / "server" / MODULE).read_bytes()
