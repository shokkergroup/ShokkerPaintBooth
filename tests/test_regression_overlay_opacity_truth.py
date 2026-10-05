"""SPB-93 Pass 117: Zone overlay slider and shortcuts share one state."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start_marker, end_marker):
    start = CANVAS.index(start_marker)
    return CANVAS[start : CANVAS.index(end_marker, start)]


def test_slider_calls_a_published_endpoint_safe_controller():
    controller = _span("function setOverlayOpacity(val)", "// --- ZOOM TO SELECTION")
    assert "Number.isFinite(parsed)" in controller
    assert "Math.max(0, Math.min(2, parsed))" in controller
    assert "window.overlayOpacityMultiplier = overlayOpacityMultiplier" in controller
    assert "window.setOverlayOpacity = setOverlayOpacity" in controller
    assert "slider.value = String(Math.round(overlayOpacityMultiplier * 100))" in controller
    assert "Math.round(overlayOpacityMultiplier * 50) + '%'" in controller
    assert 'oninput="window.setOverlayOpacity(this.value / 100)"' in HTML


def test_comma_period_shortcuts_preserve_zero_and_sync_the_slider():
    source = _span("// [64] ZONE OVERLAY OPACITY shortcut", "// [65] DRAW PREVIEW")
    assert source.count("Number.isFinite(Number(window.overlayOpacityMultiplier))") == 2
    assert "window.overlayOpacityMultiplier || 1" not in source
    assert "window.setOverlayOpacity(Math.max(0, current - 0.1))" in source
    assert "window.setOverlayOpacity(Math.min(2, current + 0.1))" in source
    assert source.count("e.preventDefault()") == 2


def test_overlay_control_accessibility_reports_display_percent_not_raw_multiplier():
    assert 'aria-label="Zone overlay opacity percent"' in HTML
    assert 'aria-valuemin="0" aria-valuemax="100" aria-valuenow="50"' in HTML
    assert "Zone overlay opacity (0-100%; default 50%)" in HTML


def test_pass_117_runtime_token_and_mirror_are_current():
    assert "spb93-overlay-opacity-truth-20260717" in HTML
    server = ROOT / "electron-app/server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
