import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_gradient_math_detects_repeats_and_constrains_direction():
    script = r"""
const g = require('./js/canvas/gradient.js');
const empty = new Uint8Array(64);
const first = g.computeZoneMask(empty, 8, 8, 1, 2, 7, 2, 'linear', false, 'replace');
const repeat = g.computeZoneMask(first.mask, 8, 8, 1, 2, 7, 2, 'linear', false, 'replace');
const subtractEmpty = g.computeZoneMask(empty, 8, 8, 1, 2, 7, 2, 'linear', false, 'subtract');
const snapped = g.constrainEndpoint({x: 0, y: 0}, {x: 10, y: 4}, true);
const dirty = g.dirtyRect({x: 10, y: 10}, {x: 20, y: 14}, 100, 100, 3);
process.stdout.write(JSON.stringify({
  firstValid: first.valid,
  firstChanged: first.changed,
  repeatChanged: repeat.changed,
  subtractEmptyChanged: subtractEmpty.changed,
  snapped,
  dirty
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data["firstValid"] is True
    assert data["firstChanged"] is True
    assert data["repeatChanged"] is False
    assert data["subtractEmptyChanged"] is False
    assert abs(data["snapped"]["y"]) < 1e-9
    assert data["dirty"] == {"x": 7, "y": 7, "width": 17, "height": 11}


def test_gradient_gesture_owns_target_and_history_after_validation():
    assert "window._gradientTarget = { kind: 'layer', layerId: window._gradientTargetLayerId };" in CANVAS
    assert "window._gradientTarget = { kind: 'zone', zoneIndex: selectedZoneIndex };" in CANVAS
    assert "target && target.kind === 'layer'" in CANVAS
    assert "target && target.kind === 'zone'" in CANVAS
    assert "fillGradientMask(" in CANVAS and "target.zoneIndex" in CANVAS
    assert "_pushLayerUndo(layer, 'gradient on layer');" in CANVAS
    assert "Gradient skipped: target already matches this result" in CANVAS
    assert "Gradient skipped: layer pixels already match this result" in CANVAS
    assert "globalCompositeOperation = !fgToTransparent && layerAlpha >= 1" in CANVAS
    assert "? 'copy'" in CANVAS
    assert "_pushLayerUndo(targetLayer, 'gradient on layer');" not in CANVAS


def test_gradient_options_preview_and_runtime_mirrors_are_truthful():
    assert "const showLayerGradient = layerToolbarActive && mode === 'gradient';" in CANVAS
    assert "showBrush || showLayerFill || showLayerGradient" in CANVAS
    assert "gradientFgTransLabel.style.display = showLayerGradient ? '' : 'none';" in CANVAS
    assert "_beginGradientPreview();" in CANVAS
    assert "_restoreGradientPreviewGuide()" in CANVAS
    assert "SPBGradient.dirtyRect(" in CANVAS
    assert "_constrainGradientEndpoint(window._gradientStart, pos, e.shiftKey)" in CANVAS
    assert "js/canvas/gradient.js?v=spb93-gradient-naturalness-v2-20260715" in HTML
    assert "hold Shift to constrain to 45° increments" in HTML

    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js", "js/canvas/gradient.js"):
        assert (ROOT / relative).read_bytes() == (ROOT / "electron-app" / "server" / relative).read_bytes()
