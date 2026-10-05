"""SPB-93 Pass 156: secondary shortcuts cannot bypass authoritative safety."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _canvas_shortcut_router() -> str:
    start = CANVAS.index("document.addEventListener('keydown', (e) => {")
    end = CANVAS.index("// Number keys: context-sensitive", start)
    return CANVAS[start:end]


def _shortcut_branch(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin)]


def test_pass_156_fallback_merge_visible_never_calls_flatten():
    router = _canvas_shortcut_router()
    branch = _shortcut_branch(
        router,
        "e.shiftKey && !e.altKey && e.key.toLowerCase() === 'e'",
        "e.shiftKey && !e.altKey && e.key.toLowerCase() === 'n'",
    )
    assert "!isLayerToolbarMode()" in branch
    assert "mergeVisibleLayers()" in branch
    assert "flattenAllLayers()" not in branch


def test_pass_156_fallback_zone_selection_and_merge_down_respect_mode():
    router = _canvas_shortcut_router()
    assert "requireZoneToolbarMode('Select All')" in router
    assert "requireZoneToolbarMode('Invert Selection')" in router
    merge_down = _shortcut_branch(
        router,
        "if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === 'e')",
        "if ((e.ctrlKey || e.metaKey) && e.shiftKey && !e.altKey && e.key.toLowerCase() === 'e')",
    )
    assert "requireLayerToolbarTarget('Merge Down')" in merge_down
    assert "getSelectedLayer" in merge_down


def test_pass_156_runtime_is_cache_busted():
    assert re.search(r'paint-booth-3-canvas\.js\?v=spb93-[^"\s]+', HTML)
    assert "spb93-shortcut-fallback-parity-20260717" in HTML
    assert "spb93-layer-via-cut-20260717" in HTML
