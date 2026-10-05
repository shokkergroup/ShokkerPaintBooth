"""SPB-93 Pass 69: History Brush is reachable, stateful, and document-safe."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_retouch_menu_exposes_snapshot_and_history_brush_actions():
    assert 'id="vtSaveHistorySnapshot"' in HTML
    assert 'onclick="saveHistorySnapshot()"' in HTML
    assert 'id="vtModeHistoryBrush"' in HTML
    assert "onclick=\"setCanvasMode('history-brush')\"" in HTML
    assert 'id="historyToolOptions"' in HTML
    assert 'id="historySnapshotStatus"' in HTML
    assert 'onclick="clearHistorySnapshot()"' in HTML


def test_history_mode_has_active_button_options_and_truthful_help():
    assert "'history-brush': 'vtModeHistoryBrush'" in CANVAS
    mode_start = CANVAS.index("const showHistory = (mode === 'history-brush')")
    mode_ui = CANVAS[mode_start : CANVAS.index("const penOpts", mode_start)]
    assert "historyToolOptions" in mode_ui
    assert "syncHistorySnapshotStatus" in mode_ui
    assert "Save a snapshot, then paint the selected Layer" in CANVAS


def test_snapshot_status_and_clear_lifecycle_are_document_scoped():
    status_start = CANVAS.index("function syncHistorySnapshotStatus")
    lifecycle = CANVAS[status_start : CANVAS.index("function saveHistorySnapshot", status_start)]
    assert "Snapshot ready for this Layer" in lifecycle
    assert "Current Layer is not in the snapshot" in lifecycle
    assert "_historySnapshot = null" in lifecycle
    assert "_historySnapshotPerLayer = new Map()" in lifecycle
    assert CANVAS.count("clearHistorySnapshot(true)") >= 2

    save_start = CANVAS.index("function saveHistorySnapshot")
    save = CANVAS[save_start : CANVAS.index("function paintHistoryBrush", save_start)]
    assert "syncHistorySnapshotStatus()" in save
    assert "window.markHistorySnapshot('current Layer stack')" in save
    assert "return true" in save


def test_pass_69_runtime_is_cache_busted_and_mirrored():
    assert "spb93-history-tool-access-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
