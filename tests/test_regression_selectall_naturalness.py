import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_select_all_color_kernel_is_global_even_if_contiguous_is_requested():
    script = r"""
const w = require('./js/canvas/zone/wand-selection.js');
const rgba = new Uint8Array([
  10,10,10,255, 200,200,200,255,
  200,200,200,255, 10,10,10,255
]);
const empty = new Uint8Array(4);
const first = w.selectGlobal(rgba,2,2,0,0,empty,{
  tolerance:0,sampleSize:1,contiguous:true,antiAlias:false,mode:'replace'
});
const duplicate = w.selectGlobal(rgba,2,2,0,0,first.nextMask,{
  tolerance:0,sampleSize:1,contiguous:true,antiAlias:false,mode:'replace'
});
const subtract = w.selectGlobal(rgba,2,2,0,0,first.nextMask,{
  tolerance:0,sampleSize:1,contiguous:true,antiAlias:false,mode:'subtract'
});
process.stdout.write(JSON.stringify({
  first:Array.from(first.nextMask),
  candidates:first.candidatePixels,
  changed:first.changedPixels,
  duplicate:duplicate.changedPixels,
  subtract:Array.from(subtract.nextMask),
  subtractChanged:subtract.changedPixels
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert result.stdout == (
        '{"first":[255,0,0,255],"candidates":2,"changed":2,'
        '"duplicate":0,"subtract":[0,0,0,0],"subtractChanged":2}'
    )


def test_select_all_color_uses_shared_candidate_before_history_contract():
    mouse = CANVAS[
        CANVAS.index("} else if (canvasMode === 'selectall')"):
        CANVAS.index("} else if (canvasMode === 'edge')")
    ]
    assert "applySelectAllColorSelection" in mouse
    assert "pushUndo" not in mouse
    assert "selectAllColor(" not in mouse
    assert "subtractWandSelection(" not in mouse

    shared = CANVAS[
        CANVAS.index("function applySampledColorSelection"):
        CANVAS.index("function applyMagicWandSelection")
    ]
    assert "const targetIndex = selectedZoneIndex" in shared
    assert "window.SPBWandSelection.selectGlobal" in shared
    assert "window.SPBWandSelection.countDifferences" in shared
    assert shared.index("selectKernel(") < shared.index("pushUndo(targetIndex)")
    assert shared.index("countDifferences") < shared.index("pushUndo(targetIndex)")
    assert shared.index("pushUndo(targetIndex)") < shared.index("zone.regionMask = nextMask")

    wrapper = CANVAS[
        CANVAS.index("function applySelectAllColorSelection"):
        CANVAS.index("window.applySelectAllColorSelection")
    ]
    assert "forceGlobal: true" in wrapper
    assert "toolName: 'Select All Color'" in wrapper


def test_ctrl_a_select_all_snapshots_the_actual_mask_after_noop_validation():
    helper = CANVAS[
        CANVAS.index("function _ctxSelectAll()"):
        CANVAS.index("function _ctxTransform()")
    ]
    assert helper.index("if (alreadyFull)") < helper.index("window._spbPushZoneMaskUndoSnapshot(selectedZoneIndex)")
    assert helper.index("window._spbPushZoneMaskUndoSnapshot(selectedZoneIndex)") < helper.index("z.regionMask = new Uint8Array(size)")
    assert "pushZoneUndo" not in helper
    assert "All canvas pixels are already selected" in helper
    assert "updateRegionStatus()" in helper
    assert "renderContextActionBar()" in helper
    assert "renderZones()" in helper
    assert "window._spbPushZoneMaskUndoSnapshot = _pushZoneMaskUndoSnapshot" in CANVAS

    undo = CANVAS[
        CANVAS.index("function undoDrawStroke"):
        CANVAS.index("function redoDrawStroke")
    ]
    redo = CANVAS[
        CANVAS.index("function redoDrawStroke"):
        CANVAS.index("// ===== MAGIC WAND / FLOOD FILL =====")
    ]
    for source in (undo, redo):
        assert "updateRegionStatus()" in source
        assert "renderContextActionBar()" in source


def test_select_all_color_ui_defaults_and_packaged_mirrors_are_truthful():
    assert "mode === 'wand' || mode === 'selectall'" in CANVAS
    assert "Sample + Tolerance match the full source" in CANVAS
    assert "visible RGBA across the full source" in CANVAS
    assert "const showContiguous = (mode === 'wand' || mode === 'fill')" in CANVAS
    assert "spb93-selectall-naturalness-20260715" in HTML
    assert "click to sample matching pixels across the full visible source" in HTML

    for relative in (
        "paint-booth-v2.html",
        "paint-booth-3-canvas.js",
        "js/canvas/zone/wand-selection.js",
    ):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
