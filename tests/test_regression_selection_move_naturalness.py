import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def test_selection_move_analyzes_once_translates_sparse_pixels_and_axis_locks():
    script = r"""
const m = require('./js/canvas/zone/selection-move.js');
const mask = new Uint8Array(25);
mask[6]=255; mask[7]=128; mask[11]=64;
const analysis=m.analyzeMask(mask,5,5);
const shifted=m.translate(analysis,5,5,1,2);
const clipped=m.translate(analysis,5,5,-2,0);
const origin=m.translate(analysis,5,5,0,0);
const chained=m.translate(shifted.analysis,5,5,-1,-2);
const fullyClipped=m.translate(m.analyzeMask(Uint8Array.from([255,0,0,0]),2,2),2,2,-1,0);
process.stdout.write(JSON.stringify({
  analysis:{indices:Array.from(analysis.indices),values:Array.from(analysis.values),count:analysis.count,bounds:analysis.bounds},
  normal:m.resolveOffset({x:2,y:2},{x:5,y:4},{}),
  horizontal:m.resolveOffset({x:2,y:2},{x:5,y:4},{shiftKey:true}),
  vertical:m.resolveOffset({x:2,y:2},{x:3,y:7},{shiftKey:true}),
  stats:m.translationStats(analysis,5,5,-2,0),
  shifted:{mask:Array.from(shifted.mask),moved:shifted.movedPixels,clipped:shifted.clippedPixels},
  clipped:{mask:Array.from(clipped.mask),moved:clipped.movedPixels,clipped:clipped.clippedPixels},
  originDiff:m.countDifferences(mask,origin.mask),
  chainedDiff:m.countDifferences(mask,chained.mask),
  chainedAnalysis:{indices:Array.from(chained.analysis.indices),count:chained.analysis.count,bounds:chained.analysis.bounds},
  fullyClipped:{moved:fullyClipped.movedPixels,clipped:fullyClipped.clippedPixels,count:fullyClipped.analysis.count,bounds:fullyClipped.analysis.bounds},
  shiftedDiff:m.countDifferences(mask,shifted.mask),
  meaningful:[m.hasMeaningfulChange(analysis,0,0),m.hasMeaningfulChange(analysis,1,0)]
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data["analysis"] == {
        "indices": [6, 7, 11],
        "values": [255, 128, 64],
        "count": 3,
        "bounds": {"minX": 1, "minY": 1, "maxX": 2, "maxY": 2},
    }
    assert data["normal"] == {"dx": 3, "dy": 2}
    assert data["horizontal"] == {"dx": 3, "dy": 0}
    assert data["vertical"] == {"dx": 0, "dy": 5}
    assert data["stats"] == {"dx": -2, "dy": 0, "movedPixels": 1, "clippedPixels": 2}
    expected = [0] * 25
    expected[17], expected[18], expected[22] = 255, 128, 64
    assert data["shifted"] == {"mask": expected, "moved": 3, "clipped": 0}
    clipped_expected = [0] * 25
    clipped_expected[5] = 128
    assert data["clipped"] == {"mask": clipped_expected, "moved": 1, "clipped": 2}
    assert data["originDiff"] == 0
    assert data["chainedDiff"] == 0
    assert data["chainedAnalysis"] == {
        "indices": [6, 7, 11],
        "count": 3,
        "bounds": {"minX": 1, "minY": 1, "maxX": 2, "maxY": 2},
    }
    assert data["fullyClipped"] == {"moved": 0, "clipped": 1, "count": 0, "bounds": None}
    assert data["shiftedDiff"] == 6
    assert data["meaningful"] == [False, True]


def test_selection_move_preview_commit_cancel_and_escape_share_captured_zone():
    preview = CANVAS[
        CANVAS.index("function updateSelectionMovePreview"):
        CANVAS.index("// ── FAST OVERLAY ARC")
    ]
    assert "drag.targetZoneIndex" in preview
    assert "window.SPBSelectionMove.resolveOffset" in preview
    assert "window.SPBSelectionMove.translationStats" in preview
    assert "pushUndo" not in preview
    assert "_shiftRegionMask" not in preview
    assert "ghostCanvas.style.transform" in preview
    assert "renderRegionOverlay" not in preview

    down_start = CANVAS.index("} else if (canvasMode === 'selection-move')")
    down = CANVAS[down_start:CANVAS.index("canvas.onmouseup", down_start)]
    assert "targetZoneIndex: selectedZoneIndex" in down
    assert "window.SPBSelectionMove?.analyzeMask" in down
    assert "_beginSelectionMoveGhost(_selectionMoveDrag)" in down

    mouseup_start = CANVAS.index("canvas.onmouseup = function")
    up_start = CANVAS.index(
        "if (canvasMode === 'selection-move' && _selectionMoveDrag)", mouseup_start
    )
    up = CANVAS[up_start:CANVAS.index("if (canvasMode === 'rect' && isDrawing", up_start)]
    assert "hasMeaningfulChange" in up
    assert "zoneChanged" in up
    assert "border returned to its start" in up
    assert up.index("targetZone.regionMask = new Uint8Array(drag.baseMask)") < up.index("pushUndo(drag.targetZoneIndex)")
    assert up.index("pushUndo(drag.targetZoneIndex)") < up.index("targetZone.regionMask = drag.previewMask")

    cancel = CANVAS[
        CANVAS.index("function cancelSelectionMove"):
        CANVAS.index("window.cancelSelectionMove")
    ]
    assert "zones[drag.targetZoneIndex]" in cancel
    assert "_clearSelectionMoveGhost(drag)" in cancel
    assert "Selection move cancelled" in CANVAS
    assert "e.key === 'Escape'" in CANVAS


def test_selection_move_ui_runtime_and_packaged_mirrors_are_truthful():
    module_tag = "js/canvas/zone/selection-move.js?v=spb93-selection-nudge-bounds-fastpath-20260716"
    assert module_tag in HTML
    assert HTML.index(module_tag) < HTML.index("paint-booth-3-canvas.js?v=")
    assert "Arrow moves 1px, Shift+Arrow moves 10px" in HTML
    assert "spb93-selection-nudge-naturalness-20260716" in HTML
    assert "js/canvas/zone/selection-move.js" in MANIFEST["files"]
    assert "Arrow=1px · Shift+Arrow=10px" in CANVAS
    assert "Arrow: 1px; Shift+Arrow: 10px" in CANVAS

    for relative in (
        "paint-booth-v2.html",
        "paint-booth-3-canvas.js",
        "js/canvas/zone/selection-move.js",
    ):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()


def test_selection_nudge_is_move_border_only_sparse_burst_undo_and_quiet_feedback():
    nudge_start = CANVAS.index("function nudgeRegionSelection")
    nudge = CANVAS[
        nudge_start:CANVAS.index("document.addEventListener('pointerdown'", nudge_start)
    ]
    finish = CANVAS[
        CANVAS.index("function _finishSelectionNudgeBurst"):
        CANVAS.index("function _scheduleSelectionNudgeFinish")
    ]
    router = CANVAS[
        CANVAS.index("// [50] MOVE BORDER KEYBOARD NUDGE"):
        CANVAS.index("// [51] BLEND MODE PREVIEWS")
    ]
    assert "canvasMode !== 'selection-move'" in nudge
    assert "const targetZoneIndex = selectedZoneIndex" in nudge
    assert "window.SPBSelectionMove.translationStats" in nudge
    assert "window._spbBeginSelectionMoveGhost(_selectionNudgeBurst)" in nudge
    assert "burst.ghostCanvas.style.transform" in nudge
    assert "_shiftRegionMask" not in nudge
    assert "pushZoneUndo" not in nudge
    assert "triggerPreviewRender" not in nudge
    assert "_pushZoneMaskUndoSnapshot(burst.targetZoneIndex, burst.baseMask)" in finish
    assert "window.SPBSelectionMove.translate" in finish
    assert "zone.regionMask = translated.mask" in finish
    assert "window._spbBeginSelectionMoveGhost = _beginSelectionMoveGhost" in CANVAS
    assert "window._spbClearSelectionMoveGhost = _clearSelectionMoveGhost" in CANVAS
    assert "canvasMode !== 'selection-move'" in router
    assert "result && result.handled" in router
    assert "showToast" not in router
    undo = CANVAS[CANVAS.index("function undoDrawStroke"):CANVAS.index("function redoDrawStroke")]
    assert "_finishSelectionNudgeBurst({ silent: true, render: false })" in undo
