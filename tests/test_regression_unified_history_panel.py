import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
HISTORY = (ROOT / "js/zones/zone-undo-history-controls.js").read_text(encoding="utf-8")
STATE_ZONES = (ROOT / "paint-booth-2-state-zones.js").read_text(encoding="utf-8")


def test_history_buttons_use_cross_stack_undo_and_redo():
    assert 'onclick="undoDrawStroke()"' in HTML
    assert 'aria-label="Undo last action"' in HTML
    assert 'onclick="redoDrawStroke()"' in HTML
    assert 'aria-label="Redo last action"' in HTML
    assert "window.undoDrawStroke = undoDrawStroke" in CANVAS
    assert "window.redoDrawStroke = redoDrawStroke" in CANVAS


def test_panel_renders_the_authoritative_action_trail():
    assert "window.getUnifiedUndoHistoryEntries = getUnifiedUndoHistoryEntries" in CANVAS
    assert "window._layerUndoStack = _layerUndoStack" in CANVAS
    assert "Array.isArray(window._layerUndoStack)" in CANVAS
    assert "var _undoHistoryView = [];" in CANVAS
    assert "return _undoHistoryView.slice(-maxEntries).reverse()" in CANVAS
    assert "window.renderUndoHistoryPanel()" in CANVAS
    assert "global.getUnifiedUndoHistoryEntries(50)" in HISTORY
    assert "Layer' : entry.kind === 'pixel' ? 'Pixels'" in HISTORY
    assert "global._clearUnifiedUndoActionTrails" in HISTORY
    assert "zone-undo-history-controls.js?v=spb93-unified-history-truth-20260808e" in HTML
    assert "paint-booth-2-state-zones.js?v=spb93-zone-undo-public-preview-20260809b" in HTML


def test_live_state_script_delegates_to_the_canonical_cross_document_renderer():
    start = STATE_ZONES.index("function renderUndoHistoryPanel()")
    end = STATE_ZONES.index("\nfunction formatTimeAgo", start)
    live_renderer = STATE_ZONES[start:end]
    assert "window.SPBZoneUndoHistoryControls" in live_renderer
    assert "controller.renderPanel" in live_renderer
    assert "zoneUndoStack.length + ' actions'" not in live_renderer
    assert "renderPanel: renderPanel" in HISTORY
    assert "global.getUnifiedUndoHistoryEntries(50)" in HISTORY


def test_canonical_renderer_shows_a_real_layer_transaction_at_runtime():
    script = r"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const count = { textContent: '' };
const list = { innerHTML: '' };
const document = { getElementById(id) { return id === 'undoHistoryCount' ? count : id === 'undoHistoryList' ? list : null; } };
const sandbox = {
  document,
  getUnifiedUndoHistoryEntries() {
    return [{ kind: 'layer', label: 'free transform', timestamp: Date.now() }];
  }
};
vm.runInNewContext(source, sandbox);
const rendered = sandbox.SPBZoneUndoHistoryControls.renderPanel({
  document,
  zoneUndoStack: [],
  undoHistoryPointer: -1,
  formatTimeAgo() { return 'just now'; },
  escapeHtml(value) { return String(value); }
});
process.stdout.write(JSON.stringify({ rendered, count: count.textContent, html: list.innerHTML }));
"""
    result = subprocess.run(
        ["node", "-e", script, str(ROOT / "js/zones/zone-undo-history-controls.js")],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["rendered"] is True
    assert payload["count"] == "1 action"
    assert "Layer &middot; free transform" in payload["html"]


def test_action_trail_outlives_canvas_handler_reinstallation():
    ledger = CANVAS.index("var _undoActionTrail = [];")
    setup = CANVAS.index("function setupCanvasHandlers(canvas)")
    undo_system = CANVAS.index("// ===== UNDO SYSTEM =====")
    assert ledger < setup < undo_system
    assert CANVAS.count("var _undoActionTrail = [];") == 1
    assert CANVAS.count("var _undoHistoryView = [];") == 1


def test_redo_replay_restores_undo_without_destroying_pending_redo_actions():
    append_start = CANVAS.index("function _appendUndoAction(kind, clearRedoTrail)")
    append_end = CANVAS.index("function _discardOldestUndoAction", append_start)
    append_body = CANVAS[append_start:append_end]
    redo_start = CANVAS.index("function redoDrawStroke()")
    redo_end = CANVAS.index("window.undoDrawStroke = undoDrawStroke", redo_start)
    redo_body = CANVAS[redo_start:redo_end]

    assert "if (clearRedoTrail) _redoActionTrail.length = 0;" in append_body
    assert "_appendUndoAction(kind, true);" in append_body
    assert "function _recordRestoredUndoAction(kind)" in append_body
    assert "_appendUndoAction(kind, false);" in append_body
    assert "_recordUndoAction(" not in redo_body
    for kind in ("layer", "decal", "pixel", "zone-config", "zone-mask"):
        assert f"_recordRestoredUndoAction('{kind}')" in redo_body
