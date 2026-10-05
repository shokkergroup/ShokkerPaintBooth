import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "js/canvas/zone/selection-refine.js"
MODULE = MODULE_PATH.read_text(encoding="utf-8")
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def _node(script):
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def test_refine_morphology_is_exact_soft_mask_aware_and_edge_clipped():
    data = _node(
        r"""
const m=require('./js/canvas/zone/selection-refine.js');
const point=new Uint8Array(25); point[12]=128;
const grown=m.morph(point,5,5,1,'grow');
const restored=m.morph(grown.mask,5,5,1,'shrink');
const full=new Uint8Array(25).fill(255);
const fullGrow=m.morph(full,5,5,2,'grow');
const fullShrink=m.morph(full,5,5,1,'shrink');
const emptyShrink=m.morph(new Uint8Array(25),5,5,2,'shrink');
process.stdout.write(JSON.stringify({
  grown:Array.from(grown.mask), grownChanged:grown.changedPixels, grownSelected:grown.selectedPixels,
  restored:Array.from(restored.mask),
  fullGrow:{changed:fullGrow.changedPixels,selected:fullGrow.selectedPixels},
  fullShrink:{mask:Array.from(fullShrink.mask),changed:fullShrink.changedPixels,selected:fullShrink.selectedPixels},
  emptyShrink:{changed:emptyShrink.changedPixels,selected:emptyShrink.selectedPixels}
}));
"""
    )
    expected_grow = [0] * 25
    for index in (6, 7, 8, 11, 12, 13, 16, 17, 18):
        expected_grow[index] = 128
    expected_center = [0] * 25
    expected_center[12] = 128
    expected_shrink = [0] * 25
    for y in range(1, 4):
        for x in range(1, 4):
            expected_shrink[y * 5 + x] = 255
    assert data["grown"] == expected_grow
    assert data["grownChanged"] == 8
    assert data["grownSelected"] == 9
    assert data["restored"] == expected_center
    assert data["fullGrow"] == {"changed": 0, "selected": 25}
    assert data["fullShrink"] == {"mask": expected_shrink, "changed": 16, "selected": 9}
    assert data["emptyShrink"] == {"changed": 0, "selected": 0}


def test_fill_holes_feather_and_smooth_return_candidate_before_history():
    data = _node(
        r"""
const m=require('./js/canvas/zone/selection-refine.js');
const ring=new Uint8Array(49);
for(let y=1;y<=5;y++)for(let x=1;x<=5;x++)ring[y*7+x]=255;
ring[3*7+3]=0;
const filled=m.fillHoles(ring,7,7);
const open=new Uint8Array(ring); open[1*7+3]=0; open[2*7+3]=0;
const openFilled=m.fillHoles(open,7,7);
const solid=new Uint8Array(49);
for(let y=2;y<=4;y++)for(let x=2;x<=4;x++)solid[y*7+x]=255;
solid[0]=255;
const smoothed=m.smooth(solid,7,7);
const feathered=m.feather(solid,7,7,2);
process.stdout.write(JSON.stringify({
  fill:{changed:filled.changedPixels,center:filled.mask[24],selected:filled.selectedPixels},
  open:{changed:openFilled.changedPixels,center:openFilled.mask[24]},
  smooth:{changed:smoothed.changedPixels,island:smoothed.mask[0],center:smoothed.mask[24],selected:smoothed.selectedPixels},
  feather:{changed:feathered.changedPixels,soft:feathered.softPixels,center:feathered.mask[24]}
}));
"""
    )
    assert data["fill"] == {"changed": 1, "center": 255, "selected": 25}
    assert data["open"] == {"changed": 0, "center": 0}
    assert data["smooth"] == {"changed": 1, "island": 0, "center": 255, "selected": 9}
    assert data["feather"]["changed"] > 0
    assert data["feather"]["soft"] > 0
    assert 0 < data["feather"]["center"] < 255


def test_refine_controller_validates_noop_before_one_zone_undo_and_render():
    commit = CANVAS[
        CANVAS.index("function _commitSelectionRefine"):
        CANVAS.index("function growRegionMask", CANVAS.index("function _commitSelectionRefine"))
    ]
    assert commit.index("result.changedPixels <= 0") < commit.index("pushUndo(context.zoneIndex)")
    assert commit.index("pushUndo(context.zoneIndex)") < commit.index("context.zone.regionMask = result.mask")
    assert commit.count("pushUndo(") == 1
    assert commit.count("_refreshZoneMaskHistoryUI()") == 1
    settlement = CANVAS[
        CANVAS.index("function _refreshZoneMaskHistoryUI"):
        CANVAS.index("function pushZoneMaskUndoSnapshotForRedo")
    ]
    for call in (
        "renderRegionOverlay()", "renderZoneDetail(selectedZoneIndex)",
        "renderZones()", "updateRegionStatus()", "renderContextActionBar()",
        "triggerPreviewRender()",
    ):
        assert call in settlement
    assert "selectedLayer" not in commit
    assert "_psdLayers" not in commit
    assert "putImageData" not in commit
    assert "const boundary = []" not in CANVAS
    assert "const edgePixels = []" not in CANVAS
    refine_span = CANVAS[
        CANVAS.index("function _selectionRefineContext"):
        CANVAS.index("// --- DESELECT ---", CANVAS.index("function _selectionRefineContext"))
    ]
    assert "new Float32Array(w * h)" not in refine_span
    for name in ("morph", "fillHoles", "feather", "smooth"):
        assert f"window.SPBSelectionRefine.{name}" in CANVAS


def test_refine_commands_are_visible_truthful_and_packaged():
    module_tag = "js/canvas/zone/selection-refine.js?v=spb93-selection-refine-naturalness-20260716"
    assert module_tag in HTML
    assert HTML.index(module_tag) < HTML.index("paint-booth-3-canvas.js?v=")
    assert "spb93-selection-refine-naturalness-20260716" in HTML
    for label in (
        "Grow Selection 1 pixel", "Grow Selection 2 pixels",
        "Shrink Selection 1 pixel", "Shrink Selection 2 pixels",
        "Fill Selection Holes", "Feather Selection 2 pixels", "Smooth Edges",
    ):
        assert f'aria-label="{label}"' in HTML
    assert "Selection is already at the canvas edge" in CANVAS
    assert "No enclosed holes found" in CANVAS
    assert "Selection edge is already smooth" in CANVAS
    assert "js/canvas/zone/selection-refine.js" in MANIFEST["files"]


def test_refine_root_and_packaged_runtime_are_byte_identical():
    for relative in (
        "paint-booth-v2.html",
        "paint-booth-3-canvas.js",
        "js/canvas/zone/selection-refine.js",
    ):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
