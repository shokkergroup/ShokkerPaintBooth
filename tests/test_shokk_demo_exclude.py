"""DEMO-12: coordinate, native-size round-mask and document-transition gates."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'demo/frontend/js'


def test_native_brush_geometry_and_flat_document_transition():
    script = r"""
import fs from 'node:fs';
import assert from 'node:assert/strict';
const source = fs.readFileSync(process.argv[1], 'utf8');
const {imagePoint, decodeExclusion, encodeExclusion, paintExclusionSegment, prepareImportedZoneScopes} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
// Both fitted/letterboxed and independently zoomed/scrolled canvases map the
// exact pointer to the same native-image pixel. Non-square sources included.
let coordinateCases = 0;
for (const [width,height] of [[2048,2048],[1024,512]]) {
  for (const scale of [.125,.75,1.5,3]) {
    const rect = {left:534.75-173*scale, top:323-87*scale, width:width*scale, height:height*scale};
    const point = imagePoint({clientX:rect.left+width*.63*scale, clientY:rect.top+height*.29*scale},rect,width,height);
    assert.ok(Math.abs(point.x-width*.63)<1e-8 && Math.abs(point.y-height*.29)<1e-8);
    assert.equal(point.inside,true); coordinateCases++;
    assert.equal(imagePoint({clientX:rect.left-1,clientY:rect.top},rect,width,height).inside,false);
  }
}
const width=256,height=128,pixels=new Uint8Array(width*height);
assert.equal(paintExclusionSegment(pixels,width,height,{x:20,y:64},{x:230,y:64},10),true);
for(let x=20;x<=230;x++) assert.equal(pixels[64*width+x],2,'fast strokes have no holes');
assert.equal(pixels[64*width+9],0); assert.equal(pixels[53*width+100],0);
const encoded=encodeExclusion(pixels,width,height);
assert.deepEqual(decodeExclusion(JSON.parse(JSON.stringify(encoded)),width,height),pixels);
assert.equal(paintExclusionSegment(pixels,width,height,{x:20,y:64},{x:230,y:64},10),false,'no-op creates no undo');
paintExclusionSegment(pixels,width,height,{x:100,y:64},{x:120,y:64},8,true);
assert.equal(pixels[64*width+110],0); assert.equal(pixels[64*width+80],2);
const empty=new Uint8Array(width*height);
paintExclusionSegment(empty,width,height,{x:-40,y:0},{x:20,y:0},8);
assert.equal(empty[0],2); assert.equal(empty[width-1],0,'no opposite-edge wrap');
assert.equal(encodeExclusion(new Uint8Array(10),5,2),null);
assert.equal(decodeExclusion(encoded,128,128).some(Boolean),false,'wrong-size saved masks cannot shift to another canvas');
assert.equal(decodeExclusion({width:2,height:2,runs:[[2,99]]},2,2).some(Boolean),false);
const zones=[{id:'z',sourceLayers:['old-psd-layer'],spatialMask:encoded}];
prepareImportedZoneScopes(zones,[{id:'flattened-source'}],true,true);
assert.deepEqual(zones[0].sourceLayers,['flattened-source']); assert.equal(zones[0].sourceLayer,'flattened-source'); assert.equal(zones[0].spatialMask,null);
zones[0].spatialMask=encoded;
prepareImportedZoneScopes(zones,[{id:'flattened-source'}],true,false);
assert.equal(zones[0].spatialMask,encoded,'same-document reload retains mask');
prepareImportedZoneScopes(zones,[{id:'new-psd'}],false,true);
assert.deepEqual(zones[0].sourceLayers,[],'flat pseudo-layer does not leak to PSD');
zones[0].sourceLayers=['missing-real-psd'];
prepareImportedZoneScopes(zones,[{id:'new-psd'}],false,false);
assert.deepEqual(zones[0].sourceLayers,['missing-real-psd'],'real missing PSD scope must still fail closed');
console.log(JSON.stringify({coordinateCases, roundStroke:true, fastStroke:true, restore:true, edges:true, savedMask:true, flatImport:true}));
"""
    result = subprocess.run(['node', '--input-type=module', '-e', script, str(JS/'exclude-mask.js')], cwd=ROOT, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)['coordinateCases'] == 8


def test_exclude_ui_pipeline_and_stage_are_wired():
    app = (JS/'app.js').read_text(encoding='utf-8')
    brush = (JS/'exclude-brush.js').read_text(encoding='utf-8')
    html = (JS.parent/'paint-booth-v2.html').read_text(encoding='utf-8')
    css = (JS.parent/'styles.css').read_text(encoding='utf-8')
    stage = (ROOT/'demo/build_demo_stage.py').read_text(encoding='utf-8')
    assert "['source', 'live']" in brush
    for event in ['pointerdown','pointermove','pointerup','pointercancel','lostpointercapture']:
        assert f"addEventListener('{event}'" in brush
    assert 'setPointerCapture' in brush and 'releasePointerCapture' in brush
    assert 'event.clientX' in brush and 'getBoundingClientRect' in brush
    assert 'event.shiftKey' in brush and "event.key === 'Escape'" in brush
    assert 'remember(current.context, current.before)' in brush
    assert 'spatial_mask: zone.spatialMask || null' in app
    assert "isSingleFlatSource() ? []" in app
    assert 'prepareImportedZoneScopes(state.zones' in app
    assert 'state.previewGeneration += 1' in app
    for key in ['excludeSize','excludeSizeValue','excludeUndo','excludeClear','excludeCursor','sourceExcludeOverlay','liveExcludeOverlay']:
        assert f'id="{key}"' in html
    assert '.exclude-cursor { position: fixed' in css
    assert '.exclusion-overlay[hidden]' in css
    assert 'touch-action: none' in css
    assert 'js/exclude-brush.js' in stage and 'js/exclude-mask.js' in stage


def test_exclude_pointer_transactions_cancel_restore_undo_and_size():
    result = subprocess.run(['node', str(ROOT/'tests/demo_exclude_events.mjs')], cwd=ROOT, capture_output=True, text=True, check=True)
    assert all(json.loads(result.stdout).values())
