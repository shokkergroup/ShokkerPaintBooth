"""SPB-93 Pass 104 — retouch brushes consume feather coverage as strength."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HEALING = (ROOT / "js/canvas/layer/healing-brush.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start, end):
    a = CANVAS.index(start)
    b = CANVAS.index(end, a)
    return CANVAS[a:b]


def test_selection_coverage_helper_maps_byte_mask_to_unit_strength():
    script = r"""
const fs = require('fs');
const source = fs.readFileSync('paint-booth-3-canvas.js', 'utf8');
const match = source.match(/function _selectionCoverage\(mask, pixelIndex\) \{[\s\S]*?\n\}/);
if (!match) throw new Error('helper missing');
const fn = new Function(`${match[0]}; return _selectionCoverage;`)();
process.stdout.write(JSON.stringify([
  fn(null, 0), fn(new Uint8Array([0]), 0),
  fn(new Uint8Array([128]), 0), fn(new Uint8Array([255]), 0)
]));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True,
                            capture_output=True, check=True)
    values = json.loads(result.stdout)
    assert values[:2] == [1, 0]
    assert abs(values[2] - 128 / 255) < 1e-12
    assert values[3] == 1


def test_clone_color_pattern_pencil_and_history_multiply_alpha_by_selection():
    spans = {
        "clone": _span("function paintCloneStroke", "function drawCloneSourceIndicator"),
        "color": _span("function _paintColorBrushAt", "function paintColorBrush"),
        "pattern": _span("function paintPatternBrushAt", "window.loadPatternBrush"),
        "pencil": _span("function paintPencil", "function _pencilStrokeTo"),
        "history": _span("function paintHistoryBrush", "window.saveHistorySnapshot"),
    }
    for name, source in spans.items():
        assert "selectionCoverage" in source, name
        assert "_selectionCoverage(" in source, name
        assert ("opacity * selectionCoverage" in source
                or "falloff * opacity * selectionCoverage" in source), name


def test_retouch_strength_tools_multiply_local_effect_by_selection():
    contracts = {
        "recolor": (_span("function paintRecolor", "window.paintRecolor"), "falloff * selectionCoverage"),
        "smudge": (_span("function paintSmudge", "function _logPaintPerf"), "falloff * selectionCoverage"),
        "dodge-burn": (_span("function _paintDodgeBurn", "function paintDodge"), "strength * selectionCoverage"),
        "blur": (_span("function paintBlurBrush", "window.paintBlurBrush"), "falloff * selectionCoverage"),
        "sharpen": (_span("function paintSharpenBrush", "window.paintSharpenBrush"), "falloff * selectionCoverage"),
    }
    for name, (source, multiplier) in contracts.items():
        assert "_selectionCoverage(" in source, name
        assert multiplier in source, name


def test_healing_and_runtime_tokens_are_feather_aware_and_mirrored():
    assert "window._selectionCoverage(selection, ty * w + tx)" in HEALING
    assert "falloff * selectionCoverage" in HEALING
    assert "1.3.0-spb93-pass108-hardness-core" in HEALING
    assert "spb93-recolor-layer-sample-20260717" in HTML
    assert "spb93-retouch-selection-strength-20260717" in HTML
    assert "healing-brush.js?v=spb93-retouch-dirty-upload-20260808a" in HTML
    for relative in ("paint-booth-3-canvas.js", "paint-booth-v2.html", "js/canvas/layer/healing-brush.js"):
        assert (ROOT / relative).read_bytes() == (ROOT / "electron-app" / "server" / relative).read_bytes()
