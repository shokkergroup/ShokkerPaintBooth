import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "js" / "canvas" / "dispatch.js"
CANVAS = ROOT / "paint-booth-3-canvas.js"
HTML = ROOT / "paint-booth-v2.html"


def test_dispatch_owns_alt_intent_without_changing_exclude_or_picker_math():
    script = r"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const context = {
  console: { log(){}, warn(){} },
  localStorage: { getItem(){ return null; }, setItem(){} },
  document: { readyState: 'complete', addEventListener(){} },
  setTimeout(){},
};
context.window = context;
vm.runInNewContext(source, context);
const modes = [
  'wand','selectall','edge','grab-object','lasso',
  'clone','heal','rect','ellipse-marquee','pen','shape',
  'selection-move','zone-pick','layer-move',
  'brush','fill','colorbrush','spatial-exclude'
];
console.log(JSON.stringify(Object.fromEntries(modes.map(mode => [mode, context.getAltPointerIntent(mode)]))));
"""
    result = subprocess.run(
        ["node", "-e", script, str(DISPATCH)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    intents = json.loads(result.stdout)

    for mode in ("wand", "selectall", "edge", "grab-object", "lasso"):
        assert intents[mode] == "selection-subtract"
    for mode in ("clone", "heal"):
        assert intents[mode] == "source-sample"
    for mode in ("rect", "ellipse-marquee", "pen", "shape", "selection-move", "zone-pick", "layer-move"):
        assert intents[mode] == "tool-modifier"
    for mode in ("brush", "fill", "colorbrush", "spatial-exclude"):
        assert intents[mode] == "temporary-eyedropper"


def test_canvas_consults_dispatch_before_temporary_eyedropper():
    source = CANVAS.read_text(encoding="utf-8")
    start = source.index("// Alt+click = temporary eyedropper only")
    block = source[start : start + 1800]

    assert "window.getAltPointerIntent(canvasMode)" in block
    assert "altPointerIntent === 'temporary-eyedropper'" in block
    assert "window.sampleEyedropperPixel" in block
    assert "setForegroundColor" in block


def test_modifier_routing_assets_have_fresh_runtime_tokens():
    html = HTML.read_text(encoding="utf-8")
    assert "dispatch.js?v=spb93-easy-eight-20260903a" in html
    assert "paint-booth-3-canvas.js?v=spb-revsig-20260831a" in html
