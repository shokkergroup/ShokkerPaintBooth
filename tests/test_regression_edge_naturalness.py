import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def test_edge_kernel_detects_rgba_boundaries_and_composes_before_mutation():
    script = r"""
const e = require('./js/canvas/zone/edge-region.js');
const rgba = new Uint8Array(5*3*4);
for(let y=0;y<3;y++) for(let x=0;x<5;x++){
  const p=(y*5+x)*4;
  if(x<2){rgba[p]=255;rgba[p+1]=0;}else{rgba[p]=0;rgba[p+1]=130;}
  rgba[p+2]=0;rgba[p+3]=255;
}
const edgeMap=e.buildEdgeMap(rgba,5,3,32);
const bounded=e.buildRegion(rgba,5,3,0,1,32);
const edgeSeed=e.buildRegion(rgba,5,3,1,1,32);
const open=e.buildRegion(rgba,5,3,0,1,255);
const empty=new Uint8Array(15);
const first=e.select(rgba,5,3,0,1,empty,{tolerance:32,mode:'replace'});
const duplicate=e.select(rgba,5,3,0,1,first.nextMask,{tolerance:32,mode:'replace'});
const subtract=e.select(rgba,5,3,0,1,first.nextMask,{tolerance:32,mode:'subtract'});
process.stdout.write(JSON.stringify({
  edgeMap:Array.from(edgeMap),
  bounded:{valid:bounded.valid,pixels:bounded.candidatePixels,mask:Array.from(bounded.regionMask)},
  edgeSeed:{valid:edgeSeed.valid,reason:edgeSeed.reason,pixels:edgeSeed.candidatePixels},
  open:{valid:open.valid,pixels:open.candidatePixels},
  first:{pixels:first.candidatePixels,changed:first.changedPixels},
  duplicate:duplicate.changedPixels,
  subtract:{mask:Array.from(subtract.nextMask),changed:subtract.changedPixels}
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data["edgeMap"] == [0, 255, 255, 0, 0] * 3
    assert data["bounded"] == {
        "valid": True,
        "pixels": 3,
        "mask": [255, 0, 0, 0, 0] * 3,
    }
    assert data["edgeSeed"] == {
        "valid": False,
        "reason": "Clicked on an edge - click inside a bounded region",
        "pixels": 0,
    }
    assert data["open"] == {"valid": True, "pixels": 15}
    assert data["first"] == {"pixels": 3, "changed": 3}
    assert data["duplicate"] == 0
    assert data["subtract"]["mask"] == [0] * 15
    assert data["subtract"]["changed"] == 3


def test_edge_candidate_preview_target_and_history_share_one_contract():
    mouse = CANVAS[
        CANVAS.index("} else if (canvasMode === 'edge')"):
        CANVAS.index("} else if (canvasMode === 'fill')")
    ]
    assert "applyEdgeRegionSelection" in mouse
    assert "pushUndo" not in mouse
    assert "edgeDetectFill(" not in mouse

    apply = CANVAS[
        CANVAS.index("function applyEdgeRegionSelection"):
        CANVAS.index("window.applyEdgeRegionSelection")
    ]
    assert "const targetIndex = selectedZoneIndex" in apply
    assert "window.SPBEdgeRegion.select" in apply
    assert "window.SPBWandSelection.resolveMode" in apply
    assert "window.SPBPenPath.featherMask" in apply
    assert "selection.valid" in apply
    assert "countDifferences" in apply
    assert apply.index("SPBEdgeRegion.select") < apply.index("pushUndo(targetIndex)")
    assert apply.index("countDifferences") < apply.index("pushUndo(targetIndex)")
    assert apply.index("pushUndo(targetIndex)") < apply.index("zone.regionMask = nextMask")

    preview = CANVAS[
        CANVAS.index("function computeEdgePreview"):
        CANVAS.index("function renderEdgePreviewOverlay")
    ]
    assert "window.SPBEdgeRegion.buildEdgeMap" in preview
    assert "window.SPBEdgeRegion.edgeStrengthAt" in preview


def test_edge_ui_runtime_and_packaged_mirrors_are_truthful():
    module_tag = "js/canvas/zone/edge-region.js?v=spb93-edge-naturalness-20260715"
    assert module_tag in HTML
    assert HTML.index(module_tag) < HTML.index("paint-booth-3-canvas.js?v=")
    assert "click inside an edge-bounded region" in HTML
    assert "spb93-edge-naturalness-20260715" in HTML
    assert "js/canvas/zone/edge-region.js" in MANIFEST["files"]
    assert "mode === 'edge' && selModeEl" in CANVAS
    assert "Tolerance controls edge sensitivity" in CANVAS
    assert "Edge Preview shows the same boundary map" in CANVAS

    for relative in (
        "paint-booth-v2.html",
        "paint-booth-3-canvas.js",
        "js/canvas/zone/edge-region.js",
    ):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
