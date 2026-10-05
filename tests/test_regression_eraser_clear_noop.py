"""SPB-93 Pass 77: Clear Current Target preserves history on empty Layers."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _function(name: str, next_marker: str) -> str:
    start = CANVAS.index(f"function {name}")
    return CANVAS[start : CANVAS.index(next_marker, start)]


def test_alpha_candidate_scan_accepts_only_pixels_with_visible_alpha():
    helper = _function("_imageDataHasVisibleAlpha(imageData)", "function _clearLayerWithEraser")
    script = f"""
{helper}
const out = {{
  none: _imageDataHasVisibleAlpha(null),
  empty: _imageDataHasVisibleAlpha({{data:new Uint8ClampedArray([255,0,0,0, 4,5,6,0])}}),
  visible: _imageDataHasVisibleAlpha({{data:new Uint8ClampedArray([0,0,0,0, 9,8,7,1])}}),
}};
console.log(JSON.stringify(out));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == {"none": False, "empty": False, "visible": True}


def test_layer_clear_checks_candidate_before_consuming_history():
    clear = _function("_clearLayerWithEraser(layer)", "function _clearZoneWithEraser")
    assert clear.index("_getLayerAlphaImageData(layer)") < clear.index("_pushLayerUndo(layer, 'clear layer with eraser')")
    assert clear.index("_imageDataHasVisibleAlpha(currentPixels)") < clear.index("_pushLayerUndo(layer, 'clear layer with eraser')")
    assert "Layer is already empty" in clear
    assert "blank.width = Math.max(1, currentPixels.width || 1)" in clear


def test_pass_77_runtime_is_cache_busted_and_mirrored():
    assert "spb93-eraser-clear-noop-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
