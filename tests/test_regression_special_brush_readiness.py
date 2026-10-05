"""SPB-93 Pass 86: baked-Special brush loading is truthful and race-safe."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _span(function_name: str) -> str:
    start = CANVAS.index(f"function {function_name}")
    next_function = CANVAS.find("\nfunction ", start + 10)
    return CANVAS[start : next_function if next_function >= 0 else len(CANVAS)]


def test_missing_special_stamp_requests_one_truthful_loading_notice():
    source = _span("_drawLayerSpecialStamp")
    assert "if (!specialCanvas)" in source
    assert "warmLayerPaintSpecialCache(true);" in source
    assert "return false;" in source


def test_stale_special_requests_cannot_mutate_current_loading_ui():
    source = _span("warmLayerPaintSpecialCache")
    assert "if (_layerPaintSpecialPendingKey === key)" in source
    assert "_isCurrentLayerPaintSpecialKey(key)" in source
    assert source.count("_isCurrentLayerPaintSpecialKey(key)") >= 2
    assert "_layerPaintSpecialPendingKey = null;" in _span("setLayerPaintSourceMode")


def test_special_cache_remains_keyed_by_id_and_foreground_tint():
    source = _span("_getLayerPaintSpecialCacheKey")
    assert "_foregroundColor.toLowerCase()" in source
    assert "`${id || ''}|${tintHex}`" in source


def test_special_brush_readiness_cache_token_is_live():
    assert "spb93-special-brush-readiness-20260717" in HTML
