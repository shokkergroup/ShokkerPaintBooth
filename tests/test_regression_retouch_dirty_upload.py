import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HEALING = (ROOT / "js/canvas/layer/healing-brush.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
MANIFEST = (ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8")


def test_dirty_region_unions_clamps_and_resets_after_consume():
    script = r"""
const api = require('./js/canvas/paint-dirty-region.js');
const dirty = api.create(2048, 2048);
dirty.addCircle(100, 100, 20, 1);
dirty.addCircle(140, 120, 10, 1);
const union = dirty.consume();
dirty.addCircle(0, 0, 5, 1);
const clipped = dirty.consume();
const empty = dirty.consume();
process.stdout.write(JSON.stringify({ union, clipped, empty }));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    values = json.loads(result.stdout)
    assert values["union"] == {"x": 79, "y": 79, "width": 73, "height": 53}
    assert values["clipped"] == {"x": 0, "y": 0, "width": 7, "height": 7}
    assert values["empty"] is None


def test_layer_flush_uses_bounded_put_image_data_with_full_command_fallback():
    start = CANVAS.index("function _flushPaintImageDataToCurrentSurface()")
    end = CANVAS.index("window._flushPaintImageDataToCurrentSurface", start)
    body = CANVAS[start:end]

    assert "_activePaintDirtyRegion.consume()" in body
    assert "dirty.x, dirty.y, dirty.width, dirty.height" in body
    assert "_activeLayerCtx.putImageData(paintImageData, 0, 0);" in body
    assert body.index("if (dirty)") < body.index("dirty.x, dirty.y")


def test_every_retouch_pixel_kernel_marks_before_its_upload():
    function_pairs = [
        ("function paintCloneStroke(x, y)", "function drawCloneSourceIndicator"),
        ("function paintColorBrush(x, y)", "function swapForegroundBackground"),
        ("function paintRecolor(x, y)", "window.paintRecolor = paintRecolor"),
        ("function paintSmudge(x, y)", "function _logPaintPerf"),
        ("function paintPencil(x, y", "window.paintPencil = paintPencil"),
        ("function _paintDodgeBurn(x, y, direction)", "function paintDodge"),
        ("function paintBlurBrush(x, y)", "window.paintBlurBrush = paintBlurBrush"),
        ("function paintSharpenBrush(x, y)", "window.paintSharpenBrush = paintSharpenBrush"),
        ("function paintHistoryBrush(x, y)", "window.saveHistorySnapshot"),
    ]
    for start_marker, end_marker in function_pairs:
        start = CANVAS.index(start_marker)
        body = CANVAS[start:CANVAS.index(end_marker, start)]
        assert "_markActivePaintDirtyCircle" in body, start_marker
        assert body.index("_markActivePaintDirtyCircle") < body.index("_flushPaintImageDataToCurrentSurface"), start_marker

    assert "window._markActivePaintDirtyCircle(x, y, radius, 1);" in HEALING
    assert HEALING.index("window._markActivePaintDirtyCircle") < HEALING.index("_flushPaintImageDataToCurrentSurface")


def test_typical_80px_radius_upload_is_over_100x_smaller_than_full_2048_canvas():
    full_bytes = 2048 * 2048 * 4
    dirty_bytes = (80 * 2 + 3) ** 2 * 4
    assert full_bytes / dirty_bytes > 150


def test_dirty_region_runtime_is_loaded_cache_busted_and_packaged():
    assert "js/canvas/paint-dirty-region.js?v=spb93-retouch-dirty-upload-20260808a" in HTML
    assert "js/canvas/layer/healing-brush.js?v=spb93-retouch-dirty-upload-20260808a" in HTML
    import re
    assert re.search(r'<script src="paint-booth-3-canvas\.js\?v=[^"\s]+"></script>', HTML)
    assert '"js/canvas/paint-dirty-region.js"' in MANIFEST

    for relative in (
        "js/canvas/paint-dirty-region.js",
        "js/canvas/layer/healing-brush.js",
        "paint-booth-3-canvas.js",
        "paint-booth-v2.html",
    ):
        assert (ROOT / relative).read_bytes() == (ROOT / "electron-app/server" / relative).read_bytes()
