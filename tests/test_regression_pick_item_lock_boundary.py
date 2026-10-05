"""SPB-93 Pass 143: Pick Item respects an explicit Layer lock."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_source(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start, depth, index = match.start(), 0, match.start()
    while index < len(CANVAS):
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
            if depth == 0 and index > match.end():
                return CANVAS[start : index + 1]
        index += 1
    raise AssertionError(name)


def test_pass_143_connected_pick_refuses_without_implicitly_unlocking():
    source = _function_source("selectConnectedLayerPixelsAtPoint")
    lock_start = source.index("if (layer.locked)")
    lock_end = source.index("const pc =", lock_start)
    lock_branch = source[lock_start:lock_end]
    assert "return false" in lock_branch
    assert "unlock it before Pick Item" in lock_branch
    assert "layer.locked = false" not in source
    assert "Auto-unlocked" not in source


def test_pass_143_pointer_selects_locked_hit_but_never_dispatches_transform():
    start = CANVAS.index("if (canvasMode === 'layer-pick')")
    end = CANVAS.index("if (canvasMode === 'text')", start)
    route = CANVAS[start:end]
    select_at = route.index("selectPSDLayer(clickedLayer.id)")
    lock_at = route.index("if (clickedLayer.locked)")
    transform_at = route.index("selectConnectedLayerPixelsAtPoint(clickedLayer.id")
    assert select_at < lock_at < transform_at
    assert "e.stopPropagation();\n                        return;" in route[lock_at:transform_at]


def test_pass_143_selected_layer_pick_control_exposes_locked_ui_truth():
    panel = _function_source("renderLayerPanel")
    assert "Transform / Pick Item / Effects live above" in panel
    context = _function_source("renderContextActionBar")
    assert "_contextActionButton('Pick Item', 'activatePickItemMode()'" in context
    assert "selectedLayer.locked" in context


def test_pass_143_runtime_is_cache_busted():
    assert "spb93-pick-item-lock-boundary-20260717" in HTML
    assert re.search(r'paint-booth-3-canvas\.js\?v=spb93-[^"\s]+', HTML)
    assert "spb93-transform-undo-intent-20260717" in HTML
