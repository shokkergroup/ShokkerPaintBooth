"""SPB-93 Pass 43: transformed Layer selections bake their real alpha to Zones."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = "js/canvas/layer/layer-transform-raster.js"
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _node(script: str):
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def test_transform_alpha_uses_live_move_rotate_flip_and_preserves_soft_values():
    data = _node(
        r"""
const api=require('./js/canvas/layer/layer-transform-raster.js');
const events=[];
const rgba=new Uint8ClampedArray([0,0,0,0, 0,0,0,64, 0,0,0,128, 0,0,0,255]);
const ctx={
  save(){events.push(['save']);}, restore(){events.push(['restore']);},
  translate(x,y){events.push(['translate',x,y]);},
  scale(x,y){events.push(['scale',x,y]);}, rotate(v){events.push(['rotate',Number(v.toFixed(6))]);},
  drawImage(_img,...args){events.push(['draw',...args]);},
  getImageData(){return {data:rgba};}
};
const canvas={getContext(){return ctx;}};
const state={origImg:{id:'selected-alpha'},centerX:8,centerY:9,boxW:4,boxH:2,scaleX:-1,scaleY:1,rotation:90};
const result=api.rasterizeTransformedAlpha(state,2,2,()=>canvas);
process.stdout.write(JSON.stringify({events,mask:[...result.mask],nonZero:result.nonZero}));
"""
    )
    assert data["events"] == [
        ["save"],
        ["translate", 8, 9],
        ["scale", -1, 1],
        ["rotate", 1.570796],
        ["draw", -2, -1, 4, 2],
        ["restore"],
    ]
    assert data["mask"] == [0, 64, 128, 255]
    assert data["nonZero"] == 3


def test_zone_mask_composition_keeps_feathering_for_every_selection_mode():
    data = _node(
        r"""
const api=require('./js/canvas/layer/layer-transform-raster.js');
const current=Uint8Array.from([0,80,200,255]);
const source=Uint8Array.from([40,120,100,255]);
const modes={};
for(const mode of ['replace','add','union','subtract','intersect']){
  const result=api.combineZoneMask(current,source,mode);
  modes[mode]={mask:[...result.mask],changed:result.changed};
}
process.stdout.write(JSON.stringify(modes));
"""
    )
    assert data["replace"] == {"mask": [40, 120, 100, 255], "changed": 3}
    assert data["add"] == {"mask": [40, 120, 200, 255], "changed": 2}
    assert data["union"] == data["add"]
    assert data["subtract"] == {"mask": [0, 0, 100, 0], "changed": 3}
    assert data["intersect"] == {"mask": [0, 80, 100, 255], "changed": 1}


def test_bake_uses_transformed_alpha_zone_undo_and_layer_owned_cleanup():
    start = CANVAS.index("function bakeTransformSelectionToActiveZone()")
    end = CANVAS.index("function rotateSelectedLayerRegion", start)
    source = CANVAS[start:end]
    assert "rasterizeTransformedAlpha" in source
    assert "combineZoneMask" in source
    assert "pushZoneUndo('bake transformed selection to zone mask', true)" in source
    assert "deactivateFreeTransform(true)" in source
    assert "subLassoPoints" not in source
    assert "startsWith('selxform_')" not in source
    assert "sourceMask[i] ? 255 : 0" not in source


def test_layer_transform_live_preview_uses_the_same_negative_flip_matrix():
    """Pass 46: Flip H/V must be visible before Apply, not only after commit."""
    start = CANVAS.index("function drawTransformHandles()")
    end = CANVAS.index("function hitTestTransformHandle", start)
    source = CANVAS[start:end]
    preview_start = source.index("// Current transformed position (high quality)")
    preview_end = source.index("// Faint original position ghost", preview_start)
    preview = source[preview_start:preview_end]
    assert "transformRaster.drawTransformedSource" in preview
    assert "scaleX: s.scaleX" in preview
    assert "scaleY: s.scaleY" in preview
    assert "ctx.scale((s.scaleX || 1) < 0 ? -1 : 1" in preview
    assert "ctx.rotate(rad)" in preview


def test_transform_mask_runtime_token_and_root_mirror_contract():
    assert f"{MODULE}?v=" in HTML
    assert "spb93-transform-mask-bake-20260716" in HTML
    for relative in (MODULE, "paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
