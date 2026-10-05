"""SPB-93 Pass 68: active-tool targets must respect dispatch ownership."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_layer_only_tool_target_uses_dispatch_map_and_never_claims_a_zone():
    start = CANVAS.index("function getToolTargetSummary")
    helper = CANVAS[start : CANVAS.index("window.getToolTargetSummary", start)]
    assert "window.layerOnlyToolNames" in helper
    assert "!isLayerToolbarMode()" in helper
    assert "layer:none (switch to Layer mode)" in helper
    assert "layer:none (select editable layer)" in helper
    assert "zoneOnlyToolNames =" not in helper
    assert "layerOnlyToolNames =" not in helper


def test_both_active_label_refresh_paths_use_tool_specific_target_truth():
    switch_start = CANVAS.index("function setCanvasMode(mode)")
    switch = CANVAS[switch_start : CANVAS.index("// Toggle tool-specific controls", switch_start)]
    assert "getToolTargetSummary(mode)" in switch

    refresh_start = CANVAS.index("function refreshActiveToolLabel")
    refresh = CANVAS[refresh_start : CANVAS.index("window.refreshActiveToolLabel", refresh_start)]
    assert "getToolTargetSummary(canvasMode)" in refresh


def test_pass_68_runtime_is_cache_busted_and_mirrored():
    assert "spb93-tool-target-truth-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
