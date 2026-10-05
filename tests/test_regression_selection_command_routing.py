"""SPB-93 Pass 145: selection commands obey the visible Zone/Layer mode."""

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


def test_pass_145_copy_samples_a_layer_only_in_layer_mode():
    source = _function_source("_getSelectionSourceData")
    layer_lookup = source.index("getSelectedLayer")
    composite = source.index("sourceTarget: 'composite'")
    assert "isLayerToolbarMode()" in source[:layer_lookup]
    assert layer_lookup < composite


def test_pass_145_destructive_selection_commands_gate_locks_only_in_layer_mode():
    for name in ("cutSelection", "fillSelectionWithColor", "deleteSelection"):
        source = _function_source(name)
        diagnose = source.index("_diagnoseLayerPaintFail")
        assert "isLayerToolbarMode()" in source[:diagnose]
        assert source.index("if (layerBlockReason)") > diagnose


def test_pass_145_runtime_is_cache_busted():
    assert "spb93-selection-command-routing-20260717" in HTML
    assert re.search(r'paint-booth-3-canvas\.js\?v=spb93-[^"\s]+', HTML)
    assert "spb93-zone-layer-selection-boundary-20260717" in HTML
