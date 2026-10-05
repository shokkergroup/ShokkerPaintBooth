"""SPB-93 Pass 74: Text/Shape report and honor new-Layer ownership."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
DISPATCH = (ROOT / "js/canvas/dispatch.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_dispatch_owns_layer_creator_subset_before_editable_layer_lookup():
    assert "const layerCreatorToolNames = {" in DISPATCH
    assert "'text': 'Text'" in DISPATCH
    assert "'shape': 'Shape'" in DISPATCH
    assert "window.layerCreatorToolNames = layerCreatorToolNames" in DISPATCH
    start = DISPATCH.index("function requireLayerToolbarTarget")
    guard = DISPATCH[start : DISPATCH.index("window.requireLayerToolbarTarget", start)]
    assert guard.index("Object.values(layerCreatorToolNames).includes(toolName)") < guard.index("getSelectedEditableLayer")


def test_target_summary_distinguishes_new_layer_tools_from_pixel_editors():
    start = CANVAS.index("function getToolTargetSummary")
    helper = CANVAS[start : CANVAS.index("window.getToolTargetSummary", start)]
    assert "window.layerCreatorToolNames" in helper
    assert "layer:new (switch to Layer mode)" in helper
    assert "layer:new (created on commit)" in helper
    assert helper.index("layerCreator") < helper.index("layer:none (select editable layer)")


def test_text_and_shape_indicators_never_claim_existing_selected_layer():
    assert "Layer: New Text layer" in CANVAS
    assert "Layer: New Shape layer" in CANVAS
    assert "click to create a new Text layer" in CANVAS
    assert "drag to create a new Shape layer" in CANVAS
    assert "Text Tool (T) — click to create a new Text Layer" in HTML


def test_active_tool_label_routes_both_layer_creators_through_target_summary():
    start = CANVAS.index("function setCanvasMode(mode)")
    switch = CANVAS[start : CANVAS.index("// Toggle tool-specific controls", start)]
    assert "canvasToolUsesTargetLabel(mode)" in switch
    assert "getToolTargetSummary(mode)" in switch
    target_helper = CANVAS[CANVAS.index("function canvasToolUsesTargetLabel") : CANVAS.index("window.canvasToolUsesTargetLabel")]
    assert "'fill','gradient','text','shape'" in target_helper


def test_pass_74_runtime_is_cache_busted_and_mirrored():
    assert "spb93-layer-creator-targets-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js", "js/canvas/dispatch.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
