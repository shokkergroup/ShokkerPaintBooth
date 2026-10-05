import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
MANIFEST = (ROOT / "scripts" / "runtime-sync-manifest.json").read_text(encoding="utf-8")


def test_existing_frame_coalescer_keeps_only_latest_pending_drag_frame():
    script = r"""
const api = require('./js/canvas/frame-coalesce.js');
const rendered = [];
const scheduler = api.wrap((value) => rendered.push(value));
scheduler('old');
scheduler('latest');
scheduler.flush();
process.stdout.write(JSON.stringify({ rendered }));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    proof = json.loads(result.stdout)
    assert proof["rendered"] == ["latest"]


def test_layer_drag_uses_visual_only_frames_then_one_committed_readback():
    recomposite = CANVAS[
        CANVAS.index("function recompositeFromLayers(options)") :
        CANVAS.index("var _layerDragReorder")
    ]
    update = CANVAS[
        CANVAS.index("function updateLayerDrag(currentX, currentY)") :
        CANVAS.index("function endLayerDrag()")
    ]
    end = CANVAS[
        CANVAS.index("function endLayerDrag()") :
        CANVAS.index("// Free Transform for a PSD layer")
    ]

    assert "options.readback !== false" in recomposite
    assert "if (shouldReadback) paintImageData = ctx.getImageData" in recomposite
    assert "_scheduleLayerDragComposite();" in update
    assert "recompositeFromLayers();" not in update
    assert end.index("_layerDragCompositeScheduler.cancel()") < end.index("recompositeFromLayers();")
    assert end.index("recompositeFromLayers();") < end.index("triggerPreviewRender")


def test_layer_drag_uses_the_existing_loaded_frame_coalescer():
    token = "js/canvas/frame-coalesce.js?v=spb-coalesce-20260805a"
    assert token in HTML
    assert HTML.index(token) < HTML.index("paint-booth-3-canvas.js?v=spb93-tool-gauntlet-20260808ab")
    assert "window.SPBFrameCoalesce.wrap" in CANVAS
