import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def test_pass_101_boot_runs_the_public_tool_transition_once():
    start = CANVAS.index("window.setCanvasMode = setCanvasMode")
    block = CANVAS[start : CANVAS.index("// Expose for Photoshop round-trip", start)]
    assert "window.canvasMode = canvasMode" in block
    assert "if (!window._spbCanvasModeInitialSyncDone)" in block
    assert "window._spbCanvasModeInitialSyncDone = 'scheduled'" in block
    assert "setTimeout(function ()" in block
    assert "setCanvasMode(canvasMode)" in block
    assert "window._spbCanvasModeInitialSyncDone = true" in block


def test_pass_101_initial_sync_occurs_after_public_export():
    start = CANVAS.index("window.setCanvasMode = setCanvasMode")
    block = CANVAS[start : CANVAS.index("// Expose for Photoshop round-trip", start)]
    assert block.index("window.setCanvasMode = setCanvasMode") < block.index("setCanvasMode(canvasMode)")


def test_pass_101_runtime_is_cache_busted():
    assert re.search(r'paint-booth-3-canvas\.js\?v=spb93-[^"\s]+', HTML)
    assert "spb93-initial-tool-sync-20260717" in HTML
    assert "spb93-eyedropper-sample-truth-20260717" in HTML
