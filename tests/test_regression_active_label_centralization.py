"""SPB-93 Pass 89: every active-label refresh shares one ownership contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_set_mode_and_toolbar_refresh_use_the_same_label_helpers():
    set_start = CANVAS.index("function setCanvasMode(mode)")
    set_end = CANVAS.index("// Toggle tool-specific controls", set_start)
    set_source = CANVAS[set_start:set_end]
    refresh_start = CANVAS.index("function refreshActiveToolLabel")
    refresh_end = CANVAS.index("window.refreshActiveToolLabel", refresh_start)
    refresh_source = CANVAS[refresh_start:refresh_end]
    for source in (set_source, refresh_source):
        assert "getCanvasToolDisplayName" in source
        assert "canvasToolUsesTargetLabel" in source


def test_target_contract_covers_creators_and_every_move_pick_mode():
    start = CANVAS.index("function canvasToolUsesTargetLabel")
    end = CANVAS.index("window.canvasToolUsesTargetLabel", start)
    source = CANVAS[start:end]
    for mode in ("text", "shape", "layer-move", "layer-pick", "pick-item", "zone-pick"):
        assert f"'{mode}'" in source


def test_display_contract_has_polished_names_for_contextual_pick_tools():
    start = CANVAS.index("function getCanvasToolDisplayName")
    end = CANVAS.index("window.getCanvasToolDisplayName", start)
    source = CANVAS[start:end]
    assert "'pick-item': 'PICK ITEM'" in source
    assert "'zone-pick': 'PICK ZONE PIECE'" in source


def test_smart_region_hint_is_not_overwritten_by_a_duplicate_key():
    start = CANVAS.index("var _toolHints =")
    end = CANVAS.index("var _h = _toolHints", start)
    source = CANVAS[start:end]
    assert source.count("edge:") == 1
    assert "Shift=add" in source
    assert "Alt=subtract" in source


def test_active_label_centralization_cache_token_is_live():
    assert "spb93-active-label-centralization-20260717" in HTML
