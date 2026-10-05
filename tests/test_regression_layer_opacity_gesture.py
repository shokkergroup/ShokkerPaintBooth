from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start = match.end()
    depth = 1
    index = start
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[start : index - 1]


def test_pass_127_layer_slider_declares_a_complete_pointer_transaction():
    assert 'onpointerdown="beginLayerOpacityGesture' in CANVAS
    assert 'onfocus="beginLayerOpacityGesture' in CANVAS
    assert 'onchange="endLayerOpacityGesture' in CANVAS
    assert 'onpointercancel="cancelLayerOpacityGesture' in CANVAS
    assert 'onblur="endLayerOpacityGesture' in CANVAS
    assert "cancelLayerOpacityGesture" in CANVAS
    assert "window.beginLayerOpacityGesture = beginLayerOpacityGesture" in CANVAS
    assert "window.endLayerOpacityGesture = endLayerOpacityGesture" in CANVAS
    assert "window.cancelLayerOpacityGesture = cancelLayerOpacityGesture" in CANVAS


def test_t43_opacity_gesture_previews_privately_and_publishes_once_on_settle():
    begin = _function_body("beginLayerOpacityGesture")
    setter = _function_body("setLayerOpacity")
    end = _function_body("endLayerOpacityGesture")
    assert "snapshot: _snapshotLayerStack()" in begin
    assert "zoneSourceLayers: _snapshotZoneSourceLayers()" in begin
    assert "if (!gesture)" in setter
    assert "_pushLayerStackUndo(`opacity" in setter
    assert "if (gesture) gesture.changed = true" in setter
    assert "gesture.startOpacities.some" in end
    assert "_pushCapturedLayerStackUndo(gesture.capture" in end


def test_t43_escape_restores_opacity_without_history_or_redo_mutation():
    cancel = _function_body("cancelLayerOpacityGesture")
    assert "gesture.startOpacities.forEach" in cancel
    assert "layer.opacity = start.opacity" in cancel
    assert "_syncLayerOpacityControls(layer.id, pct)" in cancel
    assert "_scheduleLayerOpacityRecomposite()" in cancel
    assert "_pushLayerStackUndo" not in cancel
    assert "_pushCapturedLayerStackUndo" not in cancel


def test_t43_exact_opacity_is_inline_and_native_prompt_is_removed():
    assert 'type="number" min="0" max="100"' in CANVAS
    assert 'data-layer-opacity-input="${l.id}"' in CANVAS
    assert 'aria-label="Layer opacity percent"' in CANVAS
    assert "event.key==='Enter'" in CANVAS
    assert "event.key==='Escape'" in CANVAS
    assert "promptLayerOpacity" not in CANVAS
    assert "Layer opacity (0–100):" not in CANVAS


def test_pass_127_recomposite_is_animation_frame_coalesced():
    scheduler = _function_body("_scheduleLayerOpacityRecomposite")
    setter = _function_body("setLayerOpacity")
    assert "if (_layerOpacityRecompositePending) return" in scheduler
    assert "window.requestAnimationFrame(run)" in scheduler
    assert "recompositeFromLayers(" in scheduler
    assert "triggerPreviewRender()" in scheduler
    assert "_scheduleLayerOpacityRecomposite()" in setter
    assert "recompositeFromLayers()" not in setter


def test_pass_127_runtime_is_cache_busted():
    assert "spb93-layer-opacity-gesture-20260717" in HTML
    assert "spb93-recent-color-persistence-20260717" in HTML
    assert '<script src="paint-booth-3-canvas.js?v=spb-mcp-layer-target-20261004"></script>' in HTML
    assert (ROOT / "electron-app/server/paint-booth-3-canvas.js").read_bytes() == (ROOT / "paint-booth-3-canvas.js").read_bytes()
    assert (ROOT / "electron-app/server/paint-booth-v2.html").read_bytes() == (ROOT / "paint-booth-v2.html").read_bytes()
