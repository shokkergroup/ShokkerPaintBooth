"""SPB-93 Pass 149: Flatten discloses hidden-Layer and Zone-link loss."""

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


def test_pass_149_flatten_confirms_all_irreversible_relationship_loss_once():
    source = _function_source("flattenAllLayers")
    hidden = source.index("const hiddenLayers")
    confirm = source.index("const ok = confirm(", hidden)
    history = source.index("_pushLayerStackUndo('flatten all')", confirm)
    assert hidden < confirm < history
    assert "hidden Layer(s) will be discarded" in source
    assert "Zone source-Layer restriction(s) will be cleared" in source
    assert "Use Merge Visible instead if hidden Layers must survive" in source
    assert "if (!ok) return false" in source


def test_pass_149_flattened_layer_has_complete_defaults_and_honest_ui_copy():
    source = _function_source("flattenAllLayers")
    for default in ("alphaLock: false", "clippingMask: false", "effects: null"):
        assert default in source
    panel = _function_source("renderLayerPanel")
    assert "hidden Layers and Zone links are disclosed before removal" in panel
    assert "Flatten all visible layers into one" not in panel


def test_pass_149_runtime_is_cache_busted():
    assert re.search(r'paint-booth-3-canvas\.js\?v=spb93-[^"\s]+', HTML)
    assert "spb93-flatten-loss-confirmation-20260717" in HTML
    assert "spb93-empty-stack-composite-20260717" in HTML
