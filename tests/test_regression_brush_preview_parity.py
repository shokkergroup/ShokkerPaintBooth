"""SPB-93 Pass 39: fast Zone feedback matches committed brush footprints."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _between(start: str, end: str) -> str:
    start_index = CANVAS.index(start)
    return CANVAS[start_index : CANVAS.index(end, start_index)]


def test_zone_fast_overlay_traces_the_same_selected_footprint():
    source = _between("function _fastOverlayArc", "function _fastSpatialOverlayArc")
    assert "_createBrushFootprint" in source
    assert "blockEraser ? 'square' : null" in source
    assert "footprint.tracePath(ctx, cx, cy)" in source
    assert "ctx.arc(" not in source
    assert "ctx.fillRect(" not in source


def test_scoped_zone_feedback_honors_shape_but_dedicated_spatial_stays_round():
    source = _between("function _fastSpatialOverlayArc", "function _paintRegionCircleAt")
    assert "value, shapeOverride" in source
    assert "_createBrushFootprint" in source
    assert "footprint.tracePath(ctx, cx, cy)" in source
    assert "ctx.arc(" not in source
    assert "ctx.fillRect(" not in source

    # The Zone Brush call omits an override and therefore uses Brush Tip Shape.
    assert "_fastSpatialOverlayArc(dab.x, dab.y, dynamics.radius, val);" in CANVAS
    # Dedicated Spatial Include/Exclude/Erase has no visible tip-shape control.
    assert "_fastSpatialOverlayArc(pos.x, pos.y, spatialBrushRadius, val, 'round');" in CANVAS


def test_canvas_cache_token_forces_refreshed_preview_code():
    assert "spb93-brush-preview-parity-20260716" in HTML


def test_root_and_packaged_preview_runtime_are_byte_identical():
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
