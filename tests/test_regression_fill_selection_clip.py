"""SPB-93 Pass 95: Layer Fill clips solid and baked sources to selection."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _fill_span() -> str:
    start = CANVAS.index("function fillBucketOnLayer")
    return CANVAS[start : CANVAS.index("window.fillGradientOnLayer", start)]


def test_layer_fill_builds_candidate_for_special_or_active_selection():
    source = _fill_span()
    assert "const selectionMask = paintCanvas" in source
    assert "if (useSpecialBaked || selectionMask)" in source
    assert "fillCandidate = new Uint8ClampedArray(data);" in source
    assert "_applyBakedSpecialFloodFill(" in source
    assert "fillMath.applySolidFill(fillCandidate" in source


def test_fill_clip_and_difference_happen_before_history():
    source = _fill_span()
    clip = source.index("applyMask(")
    difference = source.index("fillMath.hasMaskedDifference")
    undo = source.index("_pushLayerUndo(layer, 'fill bucket on layer')")
    assert clip < difference < undo
    assert "if (fillCandidate) data.set(fillCandidate);" in source
    assert "window.SPBSelectionClip?.applyMask" in source


def test_delayed_special_fill_intent_includes_selection_fingerprint():
    fingerprint_start = CANVAS.index("function _getLayerFillSelectionFingerprint")
    intent_start = CANVAS.index("function _getLayerFillIntentKey", fingerprint_start)
    source = CANVAS[intent_start : CANVAS.index("function _isLayerFillIntentCurrent", intent_start)]
    assert "_getLayerFillSelectionFingerprint()" in source
    fingerprint = CANVAS[fingerprint_start:intent_start]
    assert "_activeSelectionMask(pc.width, pc.height)" in fingerprint
    assert "Math.imul(hash, 16777619)" in fingerprint


def test_fill_selection_clip_cache_token_is_live():
    assert "spb93-fill-selection-clip-20260717" in HTML
