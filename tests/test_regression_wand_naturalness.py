import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def test_wand_kernel_honors_sampling_alpha_connectivity_antialias_and_modes():
    script = r"""
const w = require('./js/canvas/zone/wand-selection.js');
const sampling = new Uint8Array([
  10,0,0,255, 10,0,0,255, 10,0,0,255,
  10,0,0,255, 90,0,0,255, 10,0,0,255,
  10,0,0,255, 10,0,0,255, 10,0,0,255
]);
const diagonal = new Uint8Array([
  10,10,10,255, 200,200,200,255,
  200,200,200,255, 10,10,10,255
]);
const alpha = new Uint8Array([10,10,10,255, 10,10,10,0]);
const aa = new Uint8Array([10,0,0,255, 15,0,0,255, 100,0,0,255]);
const contiguous = w.buildRegion(diagonal,2,2,0,0,{tolerance:0,sampleSize:1,contiguous:true,antiAlias:false});
const global = w.buildRegion(diagonal,2,2,0,0,{tolerance:0,sampleSize:1,contiguous:false,antiAlias:false});
const alphaMatch = w.buildRegion(alpha,2,1,0,0,{tolerance:0,sampleSize:1,contiguous:false,antiAlias:false});
const aaOff = w.buildRegion(aa,3,1,0,0,{tolerance:2,sampleSize:1,contiguous:true,antiAlias:false});
const aaOn = w.buildRegion(aa,3,1,0,0,{tolerance:2,sampleSize:1,contiguous:true,antiAlias:true});
const candidate = new Uint8Array([255,128,0]);
const current = new Uint8Array([0,128,255]);
const replace = w.composeMask(current,candidate,'replace');
const add = w.composeMask(current,candidate,'add');
const subtract = w.composeMask(current,candidate,'subtract');
process.stdout.write(JSON.stringify({
  sample1:w.sampleColor(sampling,3,3,1,1,1),
  sample3:w.sampleColor(sampling,3,3,1,1,3),
  contiguous:Array.from(contiguous.regionMask),
  global:Array.from(global.regionMask),
  alpha:Array.from(alphaMatch.regionMask),
  aaOff:Array.from(aaOff.regionMask),
  aaOn:Array.from(aaOn.regionMask),
  replace:{mask:Array.from(replace.nextMask),changed:replace.changedPixels},
  add:{mask:Array.from(add.nextMask),changed:add.changedPixels},
  subtract:{mask:Array.from(subtract.nextMask),changed:subtract.changedPixels},
  duplicate:w.composeMask(candidate,candidate,'replace').changedPixels
  ,modes:[
    w.resolveMode('replace',{}),
    w.resolveMode('replace',{shiftKey:true}),
    w.resolveMode('replace',{altKey:true}),
    w.resolveMode('add',{shiftKey:true,altKey:true})
  ]
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data["sample1"] == {"r": 90, "g": 0, "b": 0, "a": 255, "count": 1}
    assert data["sample3"] == {"r": 19, "g": 0, "b": 0, "a": 255, "count": 9}
    assert data["contiguous"] == [255, 0, 0, 0]
    assert data["global"] == [255, 0, 0, 255]
    assert data["alpha"] == [255, 0]
    assert data["aaOff"] == [255, 0, 0]
    assert data["aaOn"][0] == 255
    assert 0 < data["aaOn"][1] < 255
    assert data["aaOn"][2] == 0
    assert data["replace"] == {"mask": [255, 128, 0], "changed": 2}
    assert data["add"] == {"mask": [255, 128, 255], "changed": 1}
    assert data["subtract"] == {"mask": [0, 0, 255], "changed": 1}
    assert data["duplicate"] == 0
    assert data["modes"] == ["replace", "add", "subtract", "subtract"]


def test_wand_candidates_precede_history_and_stay_on_captured_zone():
    assert "function applyMagicWandSelection" in CANVAS
    assert "const targetIndex = selectedZoneIndex" in CANVAS
    assert "window.ensureCompositePaintSourceForZoneTool(selectionOptions.reason" in CANVAS
    assert "reason: 'magic wand'" in CANVAS
    assert "window.SPBWandSelection.select" in CANVAS
    assert "wandSampleSize" in CANVAS
    assert "wandContiguous" in CANVAS
    assert "wandAntiAlias" in CANVAS
    assert "(mode === 'wand' || mode === 'selectall') && selModeEl" in CANVAS

    apply = CANVAS[
        CANVAS.index("function applySampledColorSelection"):
        CANVAS.index("function applyMagicWandSelection")
    ]
    assert "magicWandFill(" not in apply
    assert "window.SPBWandSelection.countDifferences" in apply
    assert "no matching pixels in the current selection" in apply
    assert "selection already matches this result" in apply
    assert apply.index("SPBWandSelection.select") < apply.index("pushUndo(targetIndex)")
    assert apply.index("countDifferences") < apply.index("pushUndo(targetIndex)")
    assert apply.index("pushUndo(targetIndex)") < apply.index("zone.regionMask = nextMask")

    mouse = CANVAS[
        CANVAS.index("} else if (canvasMode === 'wand')"):
        CANVAS.index("} else if (canvasMode === 'selectall')")
    ]
    assert "applyMagicWandSelection" in mouse
    assert "pushUndo" not in mouse


def test_wand_ui_runtime_and_packaged_mirrors_are_truthful():
    module_tag = "js/canvas/zone/wand-selection.js?v=spb93-wand-naturalness-20260715"
    assert module_tag in HTML
    assert HTML.index(module_tag) < HTML.index("paint-booth-3-canvas.js?v=")
    assert "click to sample visible color; Shift adds, Alt subtracts" in HTML
    assert "js/canvas/zone/wand-selection.js" in MANIFEST["files"]
    assert "Sample + Tolerance control the match" in CANVAS
    assert "visible RGBA" in CANVAS

    for relative in (
        "paint-booth-v2.html",
        "paint-booth-3-canvas.js",
        "js/canvas/zone/wand-selection.js",
    ):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
