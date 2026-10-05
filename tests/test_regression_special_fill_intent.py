"""SPB-93 Pass 93: delayed baked-Special Fill cannot replay stale intent."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _span(function_name: str) -> str:
    start = CANVAS.index(f"function {function_name}")
    next_function = CANVAS.find("\n            function ", start + 10)
    return CANVAS[start : next_function if next_function >= 0 else len(CANVAS)]


def test_fill_intent_signature_captures_every_visible_command_input():
    source = _span("_getLayerFillIntentKey")
    assert "layer.id" in source
    assert "_getLayerPaintSpecialCacheKey" in source
    assert "_readCanvasTolerance()" in source
    assert "wandContiguous" in source
    assert "brushOpacity" in source


def test_fill_replay_requires_same_tool_toolbar_target_source_and_settings():
    source = _span("_isLayerFillIntentCurrent")
    assert "canvasMode !== 'fill'" in source
    assert "!isLayerToolbarMode()" in source
    assert "!isLayerPaintSourceSpecial()" in source
    assert "selected.id !== layerId" in source
    assert "currentSpecialId !== specialId" in source
    assert "_getLayerFillIntentKey(selected, currentSpecialId) === intentKey" in source


def test_async_fill_callback_is_guarded_before_replay():
    source = _span("fillBucketOnLayer")
    guard = "canvas && _isLayerFillIntentCurrent(pendingIntentKey, pendingLayerId, specialId)"
    assert "const pendingIntentKey = _getLayerFillIntentKey(layer, specialId);" in source
    assert guard in source
    assert source.index(guard) < source.index("fillBucketOnLayer(startX, startY, layer);")


def test_special_fill_intent_cache_token_is_live():
    assert "spb93-special-fill-intent-20260717" in HTML
