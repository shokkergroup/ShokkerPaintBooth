from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def test_eyedropper_quick_add_has_top_toolbar_dock():
    html = (REPO / "paint-booth-v2.html").read_text(encoding="utf-8")
    assert 'id="eyedropperDockTop"' in html
    assert 'id="zoomControls"' in html
    assert html.index('id="zoomControls"') < html.index('id="eyedropperDockTop"') < html.index('id="eyedropperInfo"')


def test_eyedropper_info_is_moved_not_duplicated():
    js = (REPO / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
    assert "function dockEyedropperInfoToTopToolbar()" in js
    assert "dock.appendChild(info)" in js
    assert "window.dockEyedropperInfoToTopToolbar" in js


def test_docked_eyedropper_bar_has_non_clipping_styles():
    css = (REPO / "paint-booth-v2.css").read_text(encoding="utf-8")
    assert ".eyedropper-dock-top" in css
    assert ".eyedropper-dock-top #eyedropperInfo" in css
    assert "max-width: min(620px, calc(100% - 24px));" in css
    assert "bottom: 44px;" in css
    assert ".eyedropper-dock-top:has(#eyedropperInfo" in css


def test_eyedropper_add_button_stays_reachable_at_browser_zoom():
    html = (REPO / "paint-booth-v2.html").read_text(encoding="utf-8")
    css = (REPO / "paint-booth-v2.css").read_text(encoding="utf-8")
    assert 'id="eyedropperAddColorBtn"' in html
    assert 'aria-label="Add picked color to selected zone"' in html
    start = css.index(".eyedropper-dock-top #eyedropperInfo {")
    end = css.index(".eyedropper-dock-top #eyedropperInfo > div", start)
    info_block = css[start:end]
    assert "overflow-x: auto;" in info_block
    assert "overflow-y: hidden;" in info_block
    controls_start = css.index(".eyedropper-dock-top #eyedropperZoneControls {")
    controls_end = css.index(".eyedropper-dock-top #eyedropperZoneSelect", controls_start)
    controls_block = css[controls_start:controls_end]
    assert "flex-wrap: nowrap !important;" in controls_block
    add_start = css.index(".eyedropper-dock-top #eyedropperAddColorBtn {")
    add_end = css.index("}", add_start)
    add_block = css[add_start:add_end]
    assert "flex: 0 0 auto;" in add_block
    assert "min-height: 28px;" in add_block


def test_live_preview_wheel_zoom_does_not_bubble_to_source_canvas():
    js = (REPO / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
    start = js.index("previewPane.addEventListener('wheel'")
    end = js.index("}, { passive: false });", start)
    block = js[start:end]
    assert "e.preventDefault();" in block
    assert "e.stopPropagation();" in block


def test_live_preview_paint_and_spec_zoom_are_independent():
    js = (REPO / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
    assert "var _previewZoomByPane = { paint: 1.0, spec: 1.0 };" in js
    assert "function _getPreviewZoomPane(target)" in js
    assert "_previewZoomByPane[pane]" in js
    assert "document.getElementById('livePreviewSpecImg'), document.getElementById('specChannelCanvas')" in js
    assert "document.getElementById('livePreviewImg')" in js
    assert "var _previewZoom = 1.0;" not in js


def test_spec_preview_thumbnail_avoids_bottom_render_dock():
    css = (REPO / "paint-booth-v2.css").read_text(encoding="utf-8")
    start = css.index(".preview-inner>#previewSpecPane {")
    end = css.index(".preview-inner>#previewSpecPane:hover", start)
    block = css[start:end]
    assert "top: 56px;" in block
    assert "right: 10px;" in block
    assert "bottom: 8px;" not in block
