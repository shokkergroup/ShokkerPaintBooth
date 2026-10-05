import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "js" / "canvas" / "layer" / "adjustment-preview.js"
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _node(script: str):
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_adjustment_pixel_mutators_are_deterministic_and_preserve_alpha():
    result = _node(
        """
        const api = require('./js/canvas/layer/adjustment-preview.js');
        const bright = new Uint8ClampedArray([100,150,200,77]);
        api.applyBrightnessContrast(bright, 20, 0);
        const hue = new Uint8ClampedArray([255,0,0,91]);
        api.applyHueSaturation(hue, 120, 0, 0);
        const gray = new Uint8ClampedArray([255,0,0,63]);
        api.applyHueSaturation(gray, 0, -100, 0);
        process.stdout.write(JSON.stringify({bright:[...bright],hue:[...hue],gray:[...gray]}));
        """
    )
    assert result["bright"] == [120, 170, 220, 77]
    assert result["hue"] == [0, 255, 0, 91]
    assert result["gray"] == [128, 128, 128, 63]


def test_color_dialog_mutators_match_preview_and_commit_math():
    result = _node(
        """
        const api = require('./js/canvas/layer/adjustment-preview.js');
        const gradient = new Uint8ClampedArray([255,0,0,71]);
        api.applyGradientMap(gradient, '#0000ff', '#ffff00');
        const replace = new Uint8ClampedArray([255,0,0,83]);
        api.applyColorReplace(replace, '#ff0000', '#00ff00', 0);
        process.stdout.write(JSON.stringify({gradient:[...gradient],replace:[...replace]}));
        """
    )
    assert result["gradient"] == [76, 76, 179, 71]
    assert result["replace"] == [0, 255, 0, 83]


def test_adjustment_pixel_mutators_reject_non_rgba_buffers():
    result = _node(
        """
        const api = require('./js/canvas/layer/adjustment-preview.js');
        let threw = false;
        try { api.applyBrightnessContrast(new Uint8ClampedArray(3), 0, 0); }
        catch (error) { threw = error instanceof TypeError; }
        process.stdout.write(JSON.stringify({threw}));
        """
    )
    assert result == {"threw": True}


def test_live_adjustment_session_restores_before_one_transactional_commit():
    start = CANVAS.index("function _createAdjustmentPreviewSession")
    end = CANVAS.index("function adjustBrightnessContrast", start)
    body = CANVAS[start:end]
    assert "const originalLayerImage =" in body
    assert "target.layer.img = target.canvas;" in body
    assert "target.layer.img = originalLayerImage;" in body
    assert "restoreSource(false);" in body
    assert body.index("restoreSource(false);") < body.index("_commitAdjustment(target)")
    assert "_pushLayerUndo(" not in body
    assert "pushPixelUndo(" not in body


def test_primary_adjustment_dialogs_publish_live_preview_and_keep_keyboard_contract():
    dialog_start = CANVAS.index("function _showAdjustmentDialog(spec)")
    dialog_end = CANVAS.index("if (typeof window !== 'undefined') window._showAdjustmentDialog", dialog_start)
    dialog = CANVAS[dialog_start:dialog_end]
    assert "schedulePreview();" in dialog
    assert "spec.onPreview(values.slice())" in dialog
    assert "LIVE PREVIEW · Cancel restores the original" in dialog
    assert "cancelAnimationFrame(previewFrame)" in dialog
    assert "e.key === 'Enter'" in dialog
    assert "e.key === 'Escape'" in dialog
    assert "modal.style.justifyContent = 'flex-start'" in dialog
    assert "modal.style.background = 'rgba(0, 0, 0, 0.04)'" in dialog
    assert "modal.style.setProperty('backdrop-filter', 'none', 'important')" in dialog
    assert "exactInput.type = 'number'" in dialog
    assert "sl.label + ' exact value'" in dialog
    assert "setSliderValue(exactInput.value, false)" in dialog
    assert "setSliderValue(exactInput.value, true)" in dialog

    brightness = CANVAS[CANVAS.index("function promptAdjustBrightnessContrast"):CANVAS.index("function promptAdjustHueSat")]
    hue = CANVAS[CANVAS.index("function promptAdjustHueSat"):CANVAS.index("window.promptAdjustBrightnessContrast")]
    for body, mutator in (
        (brightness, "applyBrightnessContrast"),
        (hue, "applyHueSaturation"),
    ):
        assert "_createAdjustmentPreviewSession" in body
        assert mutator in body
        assert "onPreview:" in body
        assert "session.cancel()" in body
        assert "session.commit(vals)" in body


def test_color_dialog_adjustments_publish_live_preview_and_cancel_exactly():
    dialog_start = CANVAS.index("function _openAdjustmentColorDialog(config)")
    dialog_end = CANVAS.index("function openGradientMapDialog", dialog_start)
    dialog = CANVAS[dialog_start:dialog_end]
    assert "config.onPreview(readPayload())" in dialog
    assert "requestAnimationFrame" in dialog
    assert "LIVE PREVIEW · Cancel restores the original" in dialog
    assert "_activeAdjustmentColorDialogCancel" in dialog
    assert "overlay.style.justifyContent = 'flex-start'" in dialog
    assert "overlay.style.setProperty('backdrop-filter', 'none', 'important')" in dialog
    assert "max-width:470px" in dialog

    gradient = CANVAS[CANVAS.index("function openGradientMapDialog"):CANVAS.index("window.openGradientMapDialog")]
    replace = CANVAS[CANVAS.index("function openColorReplaceDialog"):CANVAS.index("function promptAutoColorReplace")]
    assert "'gradient map', 'applyGradientMap'" in gradient
    assert "onPreview:" in gradient and "session.cancel()" in gradient and "session.commit" in gradient
    assert "'color replace', 'applyColorReplace'" in replace
    assert "active Layer only" in replace
    assert "session.cancel()" in replace and "session.commit" in replace


def test_adjustment_preview_module_loads_before_canvas_and_is_runtime_synced():
    module_tag = 'js/canvas/layer/adjustment-preview.js?v=spb93-color-dialog-live-20260808a'
    canvas_tag = 'paint-booth-3-canvas.js?v=spb-revsig-20260831a'
    assert module_tag in HTML
    assert canvas_tag in HTML
    assert HTML.index(module_tag) < HTML.index(canvas_tag)
    manifest = (ROOT / "scripts" / "runtime-sync-manifest.json").read_text(encoding="utf-8")
    assert '"js/canvas/layer/adjustment-preview.js"' in manifest
    assert MODULE.exists()
