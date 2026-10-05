'use strict';
const assert=require('node:assert/strict');
const api=require('../js/canvas/layer/paint-source-snapshot.js');
const bounds=require('../js/canvas/layer/paint-commit-bounds.js');
const surface={width:16,height:12};
const image={width:4,height:3};
const layer={id:'art',img:image,bbox:[5,4,9,7]};
function pixels(){const p={width:16,height:12,data:new Uint8ClampedArray(16*12*4)};
    for(let y=4;y<7;y++)for(let x=5;x<9;x++)p.data.set([123,87,41,127],(y*16+x)*4);return p;}
const original=pixels();
assert(api.capture(surface,layer,original));
original.data[(5*16+6)*4]=200;
const saved=api.take(surface,layer);
assert.equal(saved.data[(5*16+6)*4],123,'first mutation cannot modify the source snapshot');
assert(bounds.analyze(original,saved,0,0,null).pixelsChanged);
assert.equal(api.take(surface,layer),null,'consume/release once');
assert(api.capture(surface,layer,pixels()));
assert.equal(bounds.analyze(pixels(),api.take(surface,layer),0,0,null).pixelsChanged,false,'no-op stays no-op');
for(const bbox of [[-1,0],[0,-1],[13,0],[0,10],[0.5,0],[NaN,0]]) {
    assert.equal(api.capture(surface,{...layer,bbox},pixels()),false,'unsupported placement must retain old full-source path');
}
for(const change of [l=>l.id='other',l=>l.img={...image},l=>l.bbox=[6,4,10,7]]) {
    const current={...layer,bbox:[...layer.bbox]};assert(api.capture(surface,current,pixels()));
    change(current);assert.equal(api.take(surface,current),null,'stale target cannot reuse pixels');
}
assert(api.capture(surface,layer,pixels()));surface.width=17;
assert.equal(api.take(surface,layer),null,'resized document cannot reuse pixels');
surface.width=16;
const cropped={width:4,height:3,data:new Uint8ClampedArray(4*3*4)};
for(let i=0;i<cropped.data.length;i+=4)cropped.data.set([123,87,41,127],i);
for(let i=0;i<32;i++) {
    const active=pixels();assert(api.capture(surface,layer,active));
    const before=api.take(surface,layer);
    active.data[(i*29)%active.data.length]=i*7;
    assert.deepEqual(bounds.analyze(active,before,0,0,null),
        bounds.analyze(active,cropped,5,4,null),'full snapshot matches cropped-source origin '+i);
}
console.log('Stroke source snapshot: immutable bytes, exact no-op, consumed once, off-canvas/fractional fallback and changed-target rejection pass.');
