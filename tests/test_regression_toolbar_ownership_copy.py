"""SPB-93 Pass 73: toolbar copy tells users which data each tool mutates."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _title(button_id: str) -> str:
    match = re.search(rf'<button id="{re.escape(button_id)}"[^>]* title="([^"]+)"', HTML)
    assert match, f"missing title for {button_id}"
    return match.group(1)


def test_dual_mode_paint_tools_name_both_valid_targets():
    for button_id in ("vtModeBrush", "vtModeErase"):
        title = _title(button_id)
        assert "Zone" in title
        assert "selected Layer" in title


def test_layer_only_toolbar_titles_do_not_imply_composite_or_zone_edits():
    layer_only_buttons = (
        "vtModeColorBrush", "vtModeClone", "vtModeHealing",
        "vtModeHistoryBrush", "vtModeRecolor", "vtModeSmudge", "vtModePencil",
        "vtModeDodge", "vtModeBurn", "vtModeBlurBrush", "vtModeSharpenBrush",
    )
    for button_id in layer_only_buttons:
        assert "selected Layer" in _title(button_id), button_id

    assert "paint RGB colors directly on canvas" not in HTML
    assert "erase mask strokes" not in HTML
    assert "Text Tool (T) — click to create a new Text Layer" in HTML


def test_active_hints_keep_healing_with_the_layer_owned_retouch_group():
    assert "'clone', 'heal', 'recolor'" in CANVAS
    assert "colorbrush: 'Paint foreground RGB directly onto the selected Layer'" in CANVAS
    assert "Selected Layer only · Alt+click sets the SOURCE" in CANVAS
    assert "selected Layer only · X swaps FG/BG" in CANVAS


def test_pass_73_runtime_is_cache_busted_and_mirrored():
    assert "spb93-toolbar-ownership-truth-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
