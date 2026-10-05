import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def test_ellipse_math_matches_preview_commit_and_rejects_identical_masks():
    script = r"""
const e = require('./js/canvas/zone/ellipse-marquee.js');
const normal = e.resolveGesture({x:5,y:5},{x:9,y:7},{});
const circle = e.resolveGesture({x:5,y:5},{x:9,y:7},{shiftKey:true});
const centered = e.resolveGesture({x:5,y:5},{x:9,y:7},{altKey:true});
const centeredCircle = e.resolveGesture({x:5,y:5},{x:9,y:7},{shiftKey:true,altKey:true});
const empty = new Uint8Array(25);
const gesture = e.resolveGesture({x:1,y:1},{x:3,y:3},{});
const add = e.composeMask(empty,5,5,gesture,'add');
const duplicate = e.composeMask(add.nextMask,5,5,gesture,'add');
const subtract = e.composeMask(add.nextMask,5,5,gesture,'subtract');
const replace = e.composeMask(add.nextMask,5,5,gesture,'replace');
process.stdout.write(JSON.stringify({
  normal, circle, centered, centeredCircle,
  tiny:e.validateGesture(e.resolveGesture({x:2,y:2},{x:2,y:2},{}),2),
  valid:e.validateGesture(circle,2),
  dirty:e.dirtyRect(centered,20,20,2),
  add:{mask:Array.from(add.nextMask), enclosed:add.enclosedPixels, changed:add.changedPixels},
  duplicate:duplicate.changedPixels,
  subtract:{mask:Array.from(subtract.nextMask), changed:subtract.changedPixels},
  replace:{mask:Array.from(replace.nextMask), changed:replace.changedPixels}
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data["normal"] == {
        "start": {"x": 5, "y": 5}, "end": {"x": 9, "y": 7},
        "cx": 7, "cy": 6, "rx": 2, "ry": 1,
    }
    assert data["circle"]["rx"] == data["circle"]["ry"] == 2
    assert data["centered"] == {
        "start": {"x": 1, "y": 3}, "end": {"x": 9, "y": 7},
        "cx": 5, "cy": 5, "rx": 4, "ry": 2,
    }
    assert data["centeredCircle"]["cx"] == data["centeredCircle"]["cy"] == 5
    assert data["centeredCircle"]["rx"] == data["centeredCircle"]["ry"] == 4
    assert data["tiny"] == {"valid": False, "reason": "Selection too small"}
    assert data["valid"] == {"valid": True, "reason": ""}
    assert data["dirty"] == {"x": 0, "y": 1, "width": 12, "height": 9}
    assert data["add"]["enclosed"] > 0
    assert data["add"]["changed"] == data["add"]["enclosed"]
    assert data["duplicate"] == 0
    assert data["subtract"]["changed"] == data["add"]["changed"]
    assert data["replace"]["changed"] == 0


def test_ellipse_preview_target_escape_and_history_share_one_contract():
    assert "var _ellipseGestureState = null;" in CANVAS
    assert "targetZoneIndex = selectedZoneIndex" in CANVAS
    assert "selectedZoneIndex !== targetIndex" in CANVAS
    assert "function _captureEllipsePreview" in CANVAS
    assert "function _restoreEllipsePreviewDirty" in CANVAS
    assert "window.SPBEllipseMarquee.dirtyRect" in CANVAS
    assert "const guideScale = 1 /" in CANVAS
    assert "window.SPBEllipseMarquee.resolveGesture" in CANVAS
    assert "canvasMode !== 'pen' && canvasMode !== 'ellipse-marquee'" in CANVAS
    assert "_ellipseGestureOwnsEscape" in CANVAS
    assert "_cancelEllipseGesture();" in CANVAS

    commit = CANVAS[
        CANVAS.index("function commitEllipseSelection"):
        CANVAS.index("function _completeEllipseGesture")
    ]
    assert "window.SPBEllipseMarquee.validateGesture" in commit
    assert "window.SPBEllipseMarquee.composeMask" in commit
    assert "window.SPBPenPath.featherMask" in commit
    assert "Ellipse skipped: selection already matches this result" in commit
    assert commit.index("composeMask") < commit.index("pushUndo(targetIndex)")
    assert commit.index("countDifferences") < commit.index("pushUndo(targetIndex)")
    assert "window.spbRefreshZoneMaskUI()" in commit
    assert commit.index("zone.regionMask = nextMask") < commit.index("window.spbRefreshZoneMaskUI()")


def test_ellipse_ui_runtime_and_packaged_mirrors_are_truthful():
    module_tag = "js/canvas/zone/ellipse-marquee.js?v=spb93-ellipse-naturalness-20260715"
    assert module_tag in HTML
    assert HTML.index(module_tag) < HTML.index("paint-booth-3-canvas.js?v=")
    assert "Shift makes a circle, Alt draws from center, Esc cancels" in HTML
    assert "js/canvas/zone/ellipse-marquee.js" in MANIFEST["files"]
    assert "Zone selection · Shift=circle · Alt=center · Esc=cancel" in CANVAS
    assert "mode === 'ellipse-marquee' && selModeEl" in CANVAS

    for relative in (
        "paint-booth-v2.html",
        "paint-booth-3-canvas.js",
        "js/canvas/zone/ellipse-marquee.js",
    ):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
