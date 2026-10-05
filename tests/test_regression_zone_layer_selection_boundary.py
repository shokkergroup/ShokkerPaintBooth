"""SPB-93 Pass 144: Zone selection tools never mutate Layer pixels implicitly."""

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


def test_pass_144_lasso_and_pen_only_commit_zone_selection_geometry():
    lasso = _function_source("closeLasso")
    pen = _function_source("penPathToMask")
    for source in (lasso, pen):
        assert "zone.regionMask" in source
        assert "maybeAutoTransformLayerSelection" not in source
        assert "transformSelectedLayerRegion" not in source
        assert "liftSelectionToNewLayer" not in source
    assert "Path converted to Zone selection" in pen


def test_pass_144_layer_context_explains_the_explicit_bridge():
    panel = _function_source("renderContextActionBar")
    assert "select it in Zone mode, return to Layer mode, then use Transform Selection" in panel
    assert "rectangle or ellipse on the selected layer jumps straight into transform" not in panel


def test_pass_144_runtime_is_cache_busted():
    assert "spb93-zone-layer-selection-boundary-20260717" in HTML
    assert "paint-booth-3-canvas.js?v=spb-revsig-20260831a" in HTML
    assert "spb93-pick-item-lock-boundary-20260717" in HTML
