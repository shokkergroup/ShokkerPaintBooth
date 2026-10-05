"""SPB-93 Pass 87: Layer manipulation cannot steal unrelated tool clicks."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
DISPATCH = (ROOT / "js/canvas/dispatch.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_layer_drag_requires_an_explicit_manipulation_mode_or_ctrl_escape_hatch():
    # Execute the actual gate: cross-layer picks must bypass selected-Layer move,
    # including Ctrl, while ordinary Move and the non-paint Ctrl escape survive.
    import subprocess
    subprocess.run(["node", "tests/object_pick_resolution_contract.cjs"], cwd=ROOT, check=True)


def test_locked_selected_layer_cannot_be_moved_or_transformed_by_explicit_tools():
    start = CANVAS.index("const _spbPaintToolActive")
    end = CANVAS.index("// === END LAYER DRAG ===", start)
    source = CANVAS[start:end]
    locked_guard = source.index("selLayer.locked")
    element_pick = source.index("_spbHoverElementBbox")
    whole_drag = source.index("startLayerDrag")
    assert locked_guard < element_pick
    assert locked_guard < whole_drag
    assert "unlock it before moving or transforming" in source


def test_dispatch_owns_explicit_layer_move_and_pick_but_unified_pick_stays_contextual():
    assert "'layer-move': 'Move Layer or Element'" in DISPATCH
    assert "'layer-pick': 'Pick Layer Element'" in DISPATCH
    layer_map = DISPATCH[DISPATCH.index("const layerOnlyToolNames") : DISPATCH.index("const layerCreatorToolNames")]
    assert "'pick-item'" not in layer_map


def test_move_and_pick_modes_surface_the_real_active_target():
    start = CANVAS.index("function canvasToolUsesTargetLabel")
    end = CANVAS.index("window.canvasToolUsesTargetLabel", start)
    source = CANVAS[start:end]
    for mode in ("layer-move", "layer-pick", "pick-item", "zone-pick"):
        assert f"'{mode}'" in source


def test_layer_manipulation_routing_tokens_are_live():
    import re
    scripts = re.findall(r'<script src="([^"]+)"', HTML)
    canvas = next(i for i, src in enumerate(scripts) if src.startswith('paint-booth-3-canvas.js?'))
    workflow = next(i for i, src in enumerate(scripts) if src.startswith('js/canvas/tool-workflow.js?'))
    assert workflow > canvas
    assert scripts[canvas].split('?')[1] == scripts[workflow].split('?')[1]
