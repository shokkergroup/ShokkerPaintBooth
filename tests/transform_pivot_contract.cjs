const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('paint-booth-3-canvas.js','utf8');
function declaration(name){const start=source.indexOf('function '+name+'() {');return source.slice(start,source.indexOf('window.'+name,start));}
const ctx={window:{},drawTransformHandles(){},renderContextActionBar(){},showToast(){},_isZoneFreeTransformTarget:t=>t==='zone-base'};
vm.runInNewContext(declaration('resetLayerTransformPivot')+declaration('resetTransformPivot'),ctx);
for(const scope of ['whole','element','group'])for(const fn of ['resetTransformPivot','resetLayerTransformPivot']){
 const state={target:'layer',centerX:970.5,centerY:1250,origCenterX:850.5,origCenterY:1179,
 boxW:240,boxH:380,rotation:30,scaleX:-0.75,scaleY:0.75,localPivotDeltaX:10,localPivotDeltaY:20};
 if(scope!=='whole')state.subRect={x1:850.5,y1:1060,x2:1090.5,y2:1440};
 if(scope==='group')state.sourceMembers=[{x1:1,y1:2,x2:3,y2:4}];
 ctx.freeTransformState=structuredClone(state);delete state.localPivotDeltaX;delete state.localPivotDeltaY;
 assert.equal(ctx[fn](),true);assert.deepEqual(ctx.freeTransformState,state,scope+' preserves all raster geometry');
}
ctx.freeTransformState=null;assert.equal(ctx.resetTransformPivot(),false);
ctx.freeTransformState={target:'unsupported'};assert.equal(ctx.resetTransformPivot(),false);
ctx.freeTransformState={target:'zone-base',centerX:200,centerY:300,origCenterX:100,origCenterY:150};
assert.equal(ctx.resetLayerTransformPivot(),false,'Layer entry never mutates Zone');
assert.equal(ctx.freeTransformState.centerX,200);
console.log('Layer Reset Pivot: actual APIs preserve moved/rotated/scaled/flipped whole, element and group geometry; guard other targets.');
