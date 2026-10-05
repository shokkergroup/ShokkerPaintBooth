const assert=require('node:assert/strict');
const api=require('../js/canvas/layer/paint-composite-region.js');
const pixels={width:6,height:5,data:Uint8ClampedArray.from({length:120},(_,i)=>i)};
function layers(){return [1,2].map(id=>({id,img:{id},visible:true,opacity:255,blendMode:'source-over',bbox:[0,0,6,5]}));}
let stack=layers(),base=api.capture(stack,2,pixels,4);
assert(api.valid(base,stack,6,5,4));
const advanced=api.afterHistory(base,stack,6,5,4,5);
assert(api.valid(advanced,stack,6,5,5));assert.equal(base.revision,4);
assert.equal(api.afterHistory(base,stack,6,5,5,6),null,'unrelated intervening revision rejects');
assert.equal(api.afterHistory(base,stack,6,5,4,6),null,'unexpected history revision rejects');
assert.equal(api.afterHistory(base,stack,6,5,4,4),null,'missing history revision rejects');
assert(!api.valid(base,stack,6,5,5));assert(!api.valid(base,stack,5,6,4));
assert(!api.valid(base,[...stack].reverse(),6,5,4));
stack[1].img={newImage:true};stack[1].bbox=[1,2,4,5];
assert(api.valid(base,stack,6,5,4),'committed active raster may be replaced/cropped');
for(const change of [l=>l.opacity=128,l=>l.visible=false,l=>l.id=9,l=>l.img={},l=>l.bbox=[1,0,6,5]]) {
 stack=layers();base=api.capture(stack,2,pixels,4);change(stack[0]);assert(!api.valid(base,stack,6,5,4));
}
for(const change of [l=>l.isGroup=true,l=>l.clippingMask=true,l=>l.groupChain=[{key:'g'}],l=>l.blendMode='multiply',l=>l.adjHue=1,l=>l.adjSat=1,l=>l.adjBri=1,l=>l.effects={shadow:{enabled:true}},l=>l.bbox=[.5,0,6,5]]) {
 stack=layers();base=api.capture(stack,2,pixels,4);change(stack[1]);
 assert(!api.eligible(stack));assert.equal(api.capture(stack,2,pixels,4),null);assert(!api.valid(base,stack,6,5,4));
}
assert.deepEqual(api.bounds({x:-1.2,y:1.2,width:4,height:9},6,5),{x:0,y:1,width:3,height:4});
for(const rect of [null,{x:8,y:0,width:1,height:1},{x:0,y:0,width:0,height:1},{x:NaN,y:0,width:1,height:1}])assert.equal(api.bounds(rect,6,5),null);
let canvases=[];
function createCanvas(){
 const canvas={width:0,height:0};
 const ctx={canvas,translate(x,y){this.offset=[x,y];},createImageData(w,h){return {width:w,height:h,data:new Uint8ClampedArray(w*h*4)};},
  getImageData(x,y,w,h){assert.deepEqual([x,y],[0,0]);assert.equal(w,canvas.width);assert.equal(h,canvas.height);return {width:w,height:h,data:new Uint8ClampedArray(w*h*4).fill(222)};},
  putImageData(data,x,y){this.published=data;assert.deepEqual([x,y],[0,0]);}};
 canvas.getContext=(kind,options)=>{assert.equal(kind,'2d');assert.equal(options.willReadFrequently,true);return ctx;};
 canvas.ctx=ctx;canvases.push(canvas);return canvas;
}
const before=pixels.data.slice();
const output=api.publish({pixels},6,5,{x:2,y:1,width:3,height:2},ctx=>{assert.deepEqual(ctx.offset,[-2,-1]);return {ok:true};},createCanvas);
assert.equal(canvases.length,2);assert.equal(output.canvas.ctx.published,output.pixels);
for(let y=0;y<5;y++)for(let x=0;x<6;x++)for(let c=0;c<4;c++){
 const i=(y*6+x)*4+c;assert.equal(output.pixels.data[i],x>=2&&x<5&&y>=1&&y<3?222:before[i]);
}
assert.deepEqual(pixels.data,before,'baseline remains immutable');
assert.deepEqual(api.publish({pixels},6,5,{x:1,y:1,width:1,height:1},()=>({ok:false,issues:['blocked']}),createCanvas),{result:{ok:false,issues:['blocked']}});
console.log('Paint composite region: stack eligibility/invalidation, exact row publication, coordinates, immutable baseline and failure fallback pass.');
