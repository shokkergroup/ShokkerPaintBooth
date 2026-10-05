import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def test_rect_math_matches_preview_commit_and_rejects_identical_masks():
    script = r"""
const r = require('./js/canvas/zone/rect-marquee.js');
const normal = r.resolveGesture({x:5,y:5},{x:9,y:7},{});
const square = r.resolveGesture({x:5,y:5},{x:9,y:7},{shiftKey:true});
const centered = r.resolveGesture({x:5,y:5},{x:9,y:7},{altKey:true});
const centeredSquare = r.resolveGesture({x:5,y:5},{x:9,y:7},{shiftKey:true,altKey:true});
const fixedRatio = r.resolveGesture({x:1,y:1},{x:9,y:3},{fixedAspect:{w:2,h:1}});
const empty = new Uint8Array(25);
const gesture = r.resolveGesture({x:1,y:1},{x:3,y:3},{});
const add = r.composeMask(empty,5,5,gesture,'add');
const duplicate = r.composeMask(add.nextMask,5,5,gesture,'add');
const subtract = r.composeMask(add.nextMask,5,5,gesture,'subtract');
const replace = r.composeMask(add.nextMask,5,5,gesture,'replace');
process.stdout.write(JSON.stringify({
  normal, square, centered, centeredSquare, fixedRatio,
  tiny:r.validateGesture(r.resolveGesture({x:2,y:2},{x:2,y:2},{}),2),
  valid:r.validateGesture(square,2),
  dirty:r.dirtyRect(centered,20,20,2),
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
        "x1": 5, "y1": 5, "x2": 9, "y2": 7, "width": 4, "height": 2,
    }
    assert data["square"]["width"] == data["square"]["height"] == 4
    assert data["centered"] == {
        "start": {"x": 1, "y": 3}, "end": {"x": 9, "y": 7},
        "x1": 1, "y1": 3, "x2": 9, "y2": 7, "width": 8, "height": 4,
    }
    assert data["centeredSquare"]["width"] == data["centeredSquare"]["height"] == 8
    assert data["fixedRatio"]["width"] == 8
    assert data["fixedRatio"]["height"] == 4
    assert data["tiny"] == {"valid": False, "reason": "Rectangle selection is too small"}
    assert data["valid"] == {"valid": True, "reason": ""}
    assert data["dirty"] == {"x": 0, "y": 1, "width": 12, "height": 9}
    assert data["add"]["enclosed"] == 9
    assert data["add"]["changed"] == 9
    assert data["duplicate"] == 0
    assert data["subtract"]["changed"] == 9
    assert data["replace"]["changed"] == 0


def test_rect_preview_target_escape_and_history_share_one_zone_contract():
    assert "let _rectGestureState = null;" in CANVAS
    assert "targetZoneIndex = selectedZoneIndex" in CANVAS
    assert "selectedZoneIndex !== targetIndex" in CANVAS
    assert "function _beginRectGesture" in CANVAS
    assert "function _updateRectGesture" in CANVAS
    assert "selBox.style.backgroundColor" in CANVAS
    assert "_rectZoneCache" not in CANVAS
    assert "e._spbRectHandled" in CANVAS
    assert "window.SPBRectMarquee.resolveGesture" in CANVAS
    assert "window.getAltPointerIntent(canvasMode)" in CANVAS
    dispatch = (ROOT / "js/canvas/dispatch.js").read_text(encoding="utf-8")
    geometry = dispatch.split("const altGeometryToolNames = new Set([", 1)[1].split("]);", 1)[0]
    assert "'rect'" in geometry and "'ellipse-marquee'" in geometry
    assert "_rectGestureOwnsEscape" in CANVAS

    commit = CANVAS[
        CANVAS.index("function commitRectSelection"):
        CANVAS.index("function _completeRectGesture")
    ]
    assert "window.SPBRectMarquee.validateGesture" in commit
    assert "window.SPBRectMarquee.composeMask" in commit
    assert "window.SPBPenPath.featherMask" in commit
    assert "Rectangle skipped: selection already matches this result" in commit
    assert "paintRegionRect" not in commit
    assert "maybeAutoTransformLayerSelection" not in commit
    assert commit.index("composeMask") < commit.index("pushUndo(targetIndex)")
    assert commit.index("countDifferences") < commit.index("pushUndo(targetIndex)")


def test_rect_ui_runtime_and_packaged_mirrors_are_truthful():
    module_tag = re.search(r'js/canvas/zone/rect-marquee\.js\?v=[^"\s]+', HTML).group(0)
    assert HTML.index(module_tag) < HTML.index("paint-booth-3-canvas.js?v=")
    assert "Shift makes a square, Alt draws from center, Esc cancels" in HTML
    assert "js/canvas/zone/rect-marquee.js" in MANIFEST["files"]
    assert "Zone selection · Shift=square · Alt=center · Esc=cancel" in CANVAS
    assert "mode === 'rect' && selModeEl" in CANVAS

    for relative in (
        "paint-booth-v2.html",
        "paint-booth-3-canvas.js",
        "js/canvas/zone/rect-marquee.js",
    ):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
