const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let created=0;
function canvas(){const calls=[];return {calls,getContext:()=>({fillRect(){},drawImage(...args){calls.push(args);}})};}
const ctx={document:{createElement(){created++;return canvas();}},SPBLayerClippingMask:{adjustFilterFor:()=> 'brightness(1.1)'}};
ctx.window=ctx;vm.runInNewContext(fs.readFileSync('js/canvas/layer/thumbnail-refresh.js','utf8'),ctx);
const layer={id:1,img:{width:100,height:50},bbox:[-10,5,90,55]},thumb=canvas(),cache=new Map();
assert.equal(ctx.SPBLayerThumbnail.draw(layer,thumb,cache,24,'a'),true);
const first=cache.get(1).canvas;
assert.deepEqual(first.calls[0],[layer.img,0,0,100,50,0,6,24,12]);
assert.equal(ctx.SPBLayerThumbnail.draw(layer,thumb,cache,24,'a'),true);
assert.equal(created,1,'unchanged thumbnail reuses cache');
layer.img={width:100,height:50};ctx.SPBLayerThumbnail.draw(layer,thumb,cache,24,'a');assert.equal(created,2,'new immutable drawable refreshes');
ctx.SPBLayerThumbnail.draw(layer,thumb,cache,24,'b');assert.equal(created,3,'changed effects refresh');
assert.equal(ctx.SPBLayerThumbnail.draw(layer,null,cache,24,'b'),false);
console.log('Layer thumbnails: aspect ratio, drawable/metadata invalidation, cache reuse and missing target pass.');
