import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def test_pen_math_constrains_handles_composes_masks_and_detects_noops():
    script = r"""
const p = require('./js/canvas/zone/pen-path.js');
const rgba = new Uint8ClampedArray(16);
rgba[3] = 255;
rgba[11] = 255;
const current = Uint8Array.from([0, 255, 0, 0]);
const add = p.composeMask(current, rgba, 'add');
const subtract = p.composeMask(current, rgba, 'subtract');
const replace = p.composeMask(current, rgba, 'replace');
process.stdout.write(JSON.stringify({
  horizontal:p.resolveHandle({x:2,y:3},{x:12,y:3},{shiftKey:true}),
  snapped:p.resolveHandle({x:0,y:0},{x:10,y:4},{shiftKey:true}),
  broken:p.resolveHandle({x:5,y:5},{x:9,y:8},{altKey:true,incoming:{x:1,y:2}}),
  add:{mask:Array.from(add.nextMask), enclosed:add.enclosedPixels, changed:add.changedPixels},
  subtract:{mask:Array.from(subtract.nextMask), enclosed:subtract.enclosedPixels, changed:subtract.changedPixels},
  replace:{mask:Array.from(replace.nextMask), enclosed:replace.enclosedPixels, changed:replace.changedPixels},
  same:p.countDifferences(current, current),
  dirty:p.dirtyRect([{x:5,y:5,cx1:1,cy1:2,cx2:9,cy2:8}],10,10,2),
  feather:Array.from(p.featherMask(Uint8Array.from([0,0,0,0,255,0,0,0,0]),3,3,1))
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data["horizontal"] == {"cx1": -8, "cy1": 3, "cx2": 12, "cy2": 3}
    assert abs(data["snapped"]["cy2"]) < 1e-9
    assert data["broken"] == {"cx1": 1, "cy1": 2, "cx2": 9, "cy2": 8}
    assert data["add"] == {"mask": [255, 255, 255, 0], "enclosed": 2, "changed": 2}
    assert data["subtract"] == {"mask": [0, 255, 0, 0], "enclosed": 2, "changed": 0}
    assert data["replace"] == {"mask": [255, 0, 255, 0], "enclosed": 2, "changed": 3}
    assert data["same"] == 0
    assert data["dirty"] == {"x": 0, "y": 0, "width": 10, "height": 10}
    assert len(data["feather"]) == 9
    assert 0 < data["feather"][4] < 255


def test_pen_preview_target_and_history_share_one_validated_contract():
    assert "var penTargetZoneIndex = null;" in CANVAS
    assert "penTargetZoneIndex = selectedZoneIndex;" in CANVAS
    assert "selectedZoneIndex !== targetIndex" in CANVAS
    assert "function _beginPenPreview()" in CANVAS
    assert "function _restorePenPreview()" in CANVAS
    assert "window.SPBPenPath.dirtyRect" in CANVAS
    assert "const guideScale = 1 / zoom;" in CANVAS
    assert "window.SPBPenPath.resolveHandle" in CANVAS
    assert "canvasMode !== 'shape' && canvasMode !== 'pen'" in CANVAS

    commit = CANVAS[CANVAS.index("function penPathToMask"): CANVAS.index("function clearPenPath")]
    assert "if (!penClosed) closePenPath();" in commit
    assert "window.SPBPenPath.composeMask" in commit
    assert "window.SPBPenPath.featherMask" in commit
    assert "Pen path needs an enclosed area" in commit
    assert "Pen path skipped: selection already matches this result" in commit
    assert commit.index("window.SPBPenPath.composeMask") < commit.index("pushUndo(targetIndex)")
    assert commit.index("countDifferences") < commit.index("pushUndo(targetIndex)")


def test_pen_ui_runtime_and_packaged_mirrors_are_truthful():
    module_tag = "js/canvas/zone/pen-path.js?v=spb93-pen-naturalness-20260715"
    assert module_tag in HTML
    assert HTML.index(module_tag) < HTML.index("paint-booth-3-canvas.js?v=")
    assert "id=\"penPathStatus\"" in HTML
    assert "Close any open path and convert it to the active Zone selection" in HTML
    assert "Shift=45° · Alt=break handles" in HTML
    assert "js/canvas/zone/pen-path.js" in MANIFEST["files"] if isinstance(MANIFEST, dict) else MANIFEST
    assert "(mode === 'lasso' || mode === 'pen')" in CANVAS
    assert "_penPathOwnsEscape" in CANVAS

    for relative in (
        "paint-booth-v2.html",
        "paint-booth-3-canvas.js",
        "js/canvas/zone/pen-path.js",
    ):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
