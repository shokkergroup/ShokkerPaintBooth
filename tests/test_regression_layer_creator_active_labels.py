"""SPB-93 Pass 81: served Text/Shape labels include their new-Layer target."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
DISPATCH = (ROOT / "js/canvas/dispatch.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_layer_creator_label_path_is_not_filtered_out_as_non_targeted():
    start = CANVAS.index("var _layerAware =")
    block = CANVAS[start : CANVAS.index("if (_layerAware && _target)", start)]
    assert "canvasToolUsesTargetLabel(mode)" in block
    contract_start = CANVAS.index("function canvasToolUsesTargetLabel")
    contract_end = CANVAS.index("window.canvasToolUsesTargetLabel", contract_start)
    contract = CANVAS[contract_start:contract_end]
    assert "'text','shape'" in contract
    assert "getToolTargetSummary(mode)" in CANVAS[CANVAS.rfind("var _target", 0, start) : start]


def test_dispatch_debug_surface_exposes_creator_contract_too():
    assert "layerCreatorTools: layerCreatorToolNames" in DISPATCH


def test_pass_81_runtime_is_cache_busted_and_mirrored():
    assert "spb93-layer-creator-active-labels-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js", "js/canvas/dispatch.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
