const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const helper=require('../js/canvas/zone/sub-piece-transform.js');
const source=fs.readFileSync('paint-booth-3-canvas.js','utf8');
assert.deepEqual(helper.bounds({minX:0,minY:0,maxX:19,maxY:39}),{x1:0,y1:0,x2:20,y2:40});
assert.deepEqual(helper.bounds(null,{x1:0,y1:0,x2:1,y2:1}),{x1:0,y1:0,x2:1,y2:1});
assert.equal(helper.bounds(null,{x1:0,y1:0,x2:0,y2:4}),null);
assert.equal(helper.bounds({minX:0,minY:NaN,maxX:20,maxY:20}),null);
function decl(name){const start=source.indexOf('function '+name+'(');let pos=source.indexOf('{',start),depth=1,end=pos+1;for(;depth;end++){if(source[end]==='{')depth++;if(source[end]==='}')depth--;}return source.slice(start,end);}
const frame={target:'base',centerX:100,centerY:80,boxW:200,boxH:160,rotation:15};
const ctx={window:{SPBZoneSubPieceTransform:helper},freeTransformState:structuredClone(frame),
 _getActiveSelectionInfo:()=>({minX:0,minY:0,maxX:19,maxY:39}),
 document:{getElementById:()=>({width:200,height:160})},drawTransformHandles(){helper.syncFrame(ctx.freeTransformState);},renderContextActionBar(){},showToast(){}};
vm.runInNewContext(decl('_isZoneFreeTransformTarget')+decl('setZoneSubRectFromSelection')+decl('clearZoneSubRect')+decl('resetTransformPivot'),ctx);
assert.equal(ctx.setZoneSubRectFromSelection(),true,'real command accepts native selection info');
let s=ctx.freeTransformState;
assert.deepEqual(helper.placement(s,200,160),{offsetX:.5,offsetY:.5,scale:1,rotation:15},'isolation does not jump material');
assert.equal(helper.unchanged(s,{offsetX:.5,offsetY:.5,scale:1,rotation:15},200,160),true);
s.centerX=30;s.centerY=40;s.boxW=40;s.boxH=80;s.rotation=90;helper.syncFrame(s);
assert.deepEqual(s.subRect,{x1:10,y1:0,x2:50,y2:80},'visible frame follows numeric placement');
assert.equal(helper.unchanged(s,{offsetX:.5,offsetY:.5,scale:1,rotation:15},200,160),false);
let p=helper.placement(s,200,160);assert.ok(Math.abs(p.offsetX-(-90/200))<1e-12);assert.ok(Math.abs(p.offsetY-220/160)<1e-12);assert.equal(p.scale,2);assert.equal(p.rotation,105);
const before=structuredClone(s);assert.equal(ctx.resetTransformPivot(),true);assert.deepEqual(s,before,'frame pivot reset preserves placement');
ctx.clearZoneSubRect();assert.equal(s.subRect,null);assert.ok(Math.abs(s.centerX+90)<1e-10);assert.equal(s.rotation,105);assert.equal(s.boxW,400);
assert.equal(helper.placement(s,200,160),null);
// Exercise the actual commit bridge and named target writer, not a copied formula.
const start=source.indexOf('const subPlacement = window.SPBZoneSubPieceTransform?.placement');
const end=source.indexOf('// v125: Zone Pattern Instance',start);
ctx.s=structuredClone(before);ctx.w=200;ctx.h=160;ctx.z={baseScale:1};
ctx.finalOffsetX=99;ctx.finalOffsetY=99;
vm.runInNewContext(decl('_setZoneFreeTransformTargetState')+source.slice(start,end),ctx);
assert.ok(Math.abs(ctx.z.baseOffsetX-(-90/200))<1e-12);assert.equal(ctx.z.baseScale,2);assert.equal(ctx.z.baseRotation,105);
const unchanged=structuredClone(ctx.freeTransformState);ctx._getActiveSelectionInfo=()=>null;
assert.equal(ctx.setZoneSubRectFromSelection(),false);assert.deepEqual(ctx.freeTransformState,unchanged,'missing selection does not mutate frame');
console.log('Zone sub-piece: real selection activation, zero-edge bounds, no-op material placement, affine movement/scale/rotation, reset/clear and actual target commit bridge.');
