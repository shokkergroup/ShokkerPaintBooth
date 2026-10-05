"""SPB-93 Pass 62: History Brush may never leak composite pixels into a Layer."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _history_source_helper() -> str:
    start = CANVAS.index("function _getHistoryBrushSourceSnapshot")
    end = CANVAS.index("window._getHistoryBrushSourceSnapshot", start)
    return CANVAS[start:end]


def test_selected_layer_without_snapshot_refuses_composite_fallback():
    helper = _history_source_helper()
    script = f"""
const window = {{}};
let _selectedLayerId = 'new-layer';
const composite = {{ kind: 'composite' }};
const layer = {{ kind: 'layer' }};
let _historySnapshot = composite;
let _historySnapshotPerLayer = new Map([['saved-layer', layer]]);
{helper}
const missing = _getHistoryBrushSourceSnapshot();
_selectedLayerId = 'saved-layer';
const saved = _getHistoryBrushSourceSnapshot();
_selectedLayerId = null;
const zone = _getHistoryBrushSourceSnapshot();
console.log(JSON.stringify({{ missing, saved: saved.kind, zone: zone.kind }}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert json.loads(result.stdout) == {"missing": None, "saved": "layer", "zone": "composite"}


def test_mousedown_blocks_missing_layer_snapshot_before_stroke_transaction():
    start = CANVAS.index("if (canvasMode === 'history-brush')")
    block = CANVAS[start : CANVAS.index("if (canvasMode === 'pencil')", start)]
    assert block.index("if (!_getHistoryBrushSourceSnapshot())") < block.index("_beginLayerPixelStroke")
    assert "Save a history snapshot that includes this layer first" in block

    painter = CANVAS[CANVAS.index("function paintHistoryBrush") : CANVAS.index("window.saveHistorySnapshot")]
    assert "const sourceSnapshot = _getHistoryBrushSourceSnapshot()" in painter
    assert "sourceSnapshot = _historySnapshot" not in painter


def test_pass_62_runtime_is_cache_busted_and_mirrored():
    assert "spb93-history-layer-isolation-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
