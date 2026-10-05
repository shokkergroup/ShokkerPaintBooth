"""SPB-93 Pass 109 — Recolor samples the Layer it edits, not composite."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _recolor_mouse_down():
    start = CANVAS.index("if (canvasMode === 'recolor')")
    end = CANVAS.index("if (canvasMode === 'smudge')", start)
    return CANVAS[start:end]


def test_recolor_samples_after_active_layer_buffer_is_acquired():
    source = _recolor_mouse_down()
    acquire = source.index("_beginLayerPixelStroke('Recolor'")
    sample = source.index("const _rd = paintImageData?.data")
    begin_math = source.index("window.SPBRecolorBrush.beginStroke")
    assert acquire < sample < begin_math
    assert "getColorAt(" not in source


def test_recolor_point_sample_is_bounds_and_alpha_safe():
    source = _recolor_mouse_down()
    assert "_rx >= 0 && _rx < _recolorCanvas.width" in source
    assert "_ry >= 0 && _ry < _recolorCanvas.height" in source
    assert "_rd[_ri + 3] > 0" in source
    assert "toHex(_rd[_ri], _rd[_ri + 1], _rd[_ri + 2])" in source
    assert "_recolorTarget =" in source


def test_runtime_token_and_mirror_are_current():
    assert "spb93-recolor-layer-sample-20260717" in HTML
    assert (ROOT / "paint-booth-3-canvas.js").read_bytes() == (
        ROOT / "electron-app/server/paint-booth-3-canvas.js"
    ).read_bytes()
