"""SPB-93 T41: free-transform numbers are live inline fields, not prompts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _slice(start_marker: str, end_marker: str) -> str:
    start = CANVAS.index(start_marker)
    end = CANVAS.index(end_marker, start)
    return CANVAS[start:end]


def test_transform_numeric_setters_do_not_open_native_prompts():
    block = _slice("function setLayerTransformRotation", "function cancelActiveTransformSession")
    assert "prompt(" not in block
    for name in (
        "setLayerTransformRotation",
        "setLayerTransformUniformScale",
        "setLayerTransformPositionAxis",
        "setZoneTransformRotation",
        "setZoneTransformUniformScale",
        "setZoneTransformPositionAxis",
    ):
        assert f"function {name}" in block
    assert "if (value === undefined) return _focusTransformNumberInput('rotation')" in block
    assert "if (value === undefined) return _focusTransformNumberInput('scale')" in block


def test_context_bar_fields_preview_live_and_preserve_transform_transaction():
    helper = _slice("function _contextActionNumberInput", "function _getZoneContextLabel")
    assert 'type="number"' in helper
    assert 'data-transform-field="${_escapeContextHtml(field)}"' in helper
    assert 'oninput="${previewExpression}"' in helper
    assert 'onchange="${commitExpression}"' in helper
    assert "this.dataset.transformStart=this.value" in helper
    assert "event.key==='Enter'" in helper
    assert "event.key==='Escape'" in helper

    render = _slice("function renderContextActionBar", "function refreshActiveToolLabel")
    for field in ("rotation", "scale", "position-x", "position-y"):
        assert f"'{field}'" in render
    assert "setLayerTransformRotation(this.value,true)" in render
    assert "setZoneTransformRotation(this.value,true)" in render
    assert "setLayerTransformPositionAxis('x',this.value,true)" in render
    assert "setZoneTransformPositionAxis('y',this.value,true)" in render
    assert "Rotation..." not in render
    assert "Scale %..." not in render
    assert "Position..." not in render


def test_numeric_previews_do_not_push_history_before_transform_apply():
    block = _slice("function setLayerTransformRotation", "function cancelActiveTransformSession")
    assert "_pushLayerStackUndo" not in block
    assert "pushUndo(" not in block
    assert block.count("drawTransformHandles()") >= 6
    assert "if (!previewOnly && typeof renderContextActionBar" in block
    assert "setLayerTransformPosition(key) : setZoneTransformPosition(key)" in CANVAS


def test_numeric_transform_build_is_cache_busted():
    assert 'src="paint-booth-3-canvas.js?v=' in HTML
