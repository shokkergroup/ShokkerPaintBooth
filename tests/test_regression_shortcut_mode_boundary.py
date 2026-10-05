"""SPB-93 Pass 147: shortcuts honor mode ownership and Photoshop Merge Visible."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
STATE = (ROOT / "paint-booth-2-state-zones.js").read_text(encoding="utf-8")
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _branch(start_marker: str, end_marker: str) -> str:
    start = STATE.index(start_marker)
    end = STATE.index(end_marker, start)
    return STATE[start:end]


def test_pass_147_zone_selection_shortcuts_cannot_bypass_layer_mode():
    select_all = _branch("} else if ((e.ctrlKey || e.metaKey) && e.key === 'a'", "} else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'I'")
    invert = _branch("} else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'I'", "} else if (e.altKey && e.key === 'Backspace')")
    for source in (select_all, invert):
        assert "isLayerToolbarMode()" in source
        assert "requireZoneToolbarMode" in source
        assert "return;" in source


def test_pass_147_layer_merge_shortcuts_cannot_bypass_zone_mode():
    merge_down = _branch("} else if ((e.ctrlKey || e.metaKey) && e.key === 'e'", "} else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'E'")
    merge_visible = _branch("} else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'E'", "} else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'N'")
    assert "!isLayerToolbarMode()" in merge_down
    assert "requireLayerToolbarTarget('Merge Down')" in merge_down
    assert "!isLayerToolbarMode()" in merge_visible
    assert "mergeVisibleLayers()" in merge_visible
    assert "flattenAllLayers()" not in merge_visible


def test_pass_147_labels_and_runtime_match_the_real_shortcut():
    assert "['Ctrl+Shift+E', 'Merge Visible Layers']" in CANVAS
    assert ">Ctrl+Shift+E</kbd> Merge Visible<" in HTML
    assert re.search(r'<script src="paint-booth-2-state-zones\.js\?v=[^"]+"', HTML)
    assert "spb93-shortcut-mode-boundary-20260717" in HTML
    assert re.search(r'<script src="paint-booth-3-canvas\.js\?v=[^"]+"', HTML)
