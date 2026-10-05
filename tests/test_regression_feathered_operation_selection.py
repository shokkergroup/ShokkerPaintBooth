"""SPB-93 Pass 103 — whole-image operations respect feather strength."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start, end):
    a = CANVAS.index(start)
    b = CANVAS.index(end, a)
    return CANVAS[a:b]


def test_half_selection_blends_in_premultiplied_space():
    script = r"""
const api = require('./js/canvas/layer/selection-clip.js');
const before = new Uint8ClampedArray([0, 0, 255, 255]);
const after = new Uint8ClampedArray([255, 0, 0, 128]);
api.applyMask(after, before, 1, 1, 0, 0, new Uint8Array([128]), 1, 1);
process.stdout.write(JSON.stringify(Array.from(after)));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, text=True,
        capture_output=True, check=True,
    )
    # Selection coverage blends both alpha and premultiplied colour, avoiding
    # the dark fringe produced by straight-RGBA interpolation.
    assert json.loads(result.stdout) == [86, 0, 169, 191]


def test_gradient_fill_and_adjustments_use_feathered_clip_before_history():
    gradient = _span("function fillGradientOnLayer", "function _applyBakedSpecialFloodFill")
    fill = _span("function fillBucketOnLayer", "function _fillMasksEqual")
    adjustment = _span("function _commitAdjustment", "function adjustBrightnessContrast")
    for source in (gradient, fill, adjustment):
        assert "window.SPBSelectionClip?.applyMask" in source
        assert "restoreOutsideMask" not in source


def test_batch_filters_attenuate_before_noop_and_history():
    source = _span("function _finishBatchPixelFilter", "function autoLevels")
    assert source.index("applyMask(data, tx.before") < source.index("if (!changed)")
    assert source.index("if (!changed)") < source.index("_pushLayerUndo")
    assert "data.set(tx.before)" in source


def test_runtime_token_and_mirror_are_current():
    assert "spb93-recolor-layer-sample-20260717" in HTML
    assert "spb93-feathered-whole-operation-selection-20260717" in HTML
    for relative in ("paint-booth-3-canvas.js", "paint-booth-v2.html", "js/canvas/layer/selection-clip.js"):
        assert (ROOT / relative).read_bytes() == (ROOT / "electron-app" / "server" / relative).read_bytes()
