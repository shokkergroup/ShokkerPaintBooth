"""SPB-93 Pass 41: moving a layer element removes its source pixels first."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = "js/canvas/layer/layer-transform-raster.js"
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def _node(script: str):
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def test_source_alpha_erase_is_scoped_and_linked_offsets_are_preserved():
    data = _node(
        r"""
const api=require('./js/canvas/layer/layer-transform-raster.js');
const events=[];
const ctx={globalCompositeOperation:'source-over',stack:[],
  save(){this.stack.push(this.globalCompositeOperation);events.push(['save',this.globalCompositeOperation]);},
  restore(){this.globalCompositeOperation=this.stack.pop();events.push(['restore',this.globalCompositeOperation]);},
  drawImage(...args){events.push(['draw',this.globalCompositeOperation,...args.slice(1)]);}};
const source={id:'source'};
const erased=api.eraseSourceAlpha(ctx,source,3,4,10,12);
process.stdout.write(JSON.stringify({
  erased, events, finalOp:ctx.globalCompositeOperation,
  linked:api.linkedPlacement({x1:100,y1:50},{x1:340,y1:175},20,30),
  invalid:api.eraseSourceAlpha(ctx,source,0,0,0,4)
}));
"""
    )
    assert data["erased"] is True
    assert data["events"] == [
        ["save", "source-over"],
        ["draw", "destination-out", 3, 4, 10, 12, 3, 4, 10, 12],
        ["restore", "source-over"],
    ]
    assert data["finalOp"] == "source-over"
    assert data["linked"] == {"x": 260, "y": 155}
    assert data["invalid"] is False


def test_master_linked_group_and_instances_erase_before_composite():
    start = CANVAS.index("const isLayerSubRect = (s.target === 'layer' && !!s.subRect);")
    end = CANVAS.index("// === Whole-layer commit path ===", start)
    source = CANVAS[start:end]
    assert "eraseTransformSourceAlpha(destCtx, s.origImg, srcX, srcY, srcW, srcH);" in source
    assert "eraseTransformSourceAlpha(destCtx, s.origImg, mSrcX, mSrcY, mSrcW, mSrcH);" in source
    assert "eraseTransformSourceAlpha(destCtx, s.origImg, instSrcX, instSrcY, instSrcW, instSrcH);" in source
    assert source.index("eraseTransformSourceAlpha(destCtx, s.origImg, srcX") < source.index(
        "destCtx.drawImage(subTmp, drawX, drawY"
    )
    assert "transformRaster.linkedPlacement(currentBboxForGroup, member, drawX, drawY)" in source
    assert "destCtx.drawImage(mSubTmp, drawX, drawY" not in source


def test_transform_raster_contract_loads_before_canvas_and_is_packaged():
    tag = f"{MODULE}?v="
    assert tag in HTML
    assert HTML.index(tag) < HTML.index("paint-booth-3-canvas.js?v=")
    assert "spb93-transform-mask-bake-20260716" in HTML
    assert MODULE in MANIFEST["files"]


def test_root_and_packaged_transform_runtime_are_byte_identical():
    for relative in (MODULE, "paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
