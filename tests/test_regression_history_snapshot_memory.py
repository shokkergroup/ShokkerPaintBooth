"""SPB-93 Pass 70: History snapshots scale with Layer bboxes, not canvas×layers."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_per_layer_history_snapshots_are_compact_and_origin_aware():
    start = CANVAS.index("function saveHistorySnapshot")
    save = CANVAS[start : CANVAS.index("function paintHistoryBrush", start)]
    assert "const iw = Math.max" in save and "const ih = Math.max" in save
    assert "lc.width = iw; lc.height = ih" in save
    assert "lctx.drawImage(layer.img, 0, 0)" in save
    assert "originX: bx" in save and "originY: by" in save
    assert "lc.width = pc.width" not in save
    assert "lctx.drawImage(layer.img, bx, by)" not in save


def test_history_brush_maps_canvas_coordinates_into_compact_snapshot():
    start = CANVAS.index("function paintHistoryBrush")
    painter = CANVAS[start : CANVAS.index("window.saveHistorySnapshot", start)]
    for contract in (
        "sourceSnapshot.width",
        "sourceSnapshot.height",
        "sourceSnapshot.originX",
        "sourceSnapshot.originY",
        "const sourceX = px - srcOriginX",
        "sourceY = py - srcOriginY",
        "_historyTransparentPixel",
        "const sampleIndex = insideSource",
    ):
        assert contract in painter


def test_pass_70_runtime_is_cache_busted_and_mirrored():
    assert "spb93-compact-history-snapshots-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
