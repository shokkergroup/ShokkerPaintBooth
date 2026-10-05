const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const code=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const guardStart=code.indexOf('const _spbPaintToolActive');
const guardEnd=code.indexOf('if (_selectedLayerId && _psdLayersLoaded',guardStart);
const guards=code.slice(guardStart,guardEnd)+'\n_spbExplicitLayerManipulation || _spbCtrlLayerDrag;';
for (const ctrlKey of [false,true]) {
 for (const canvasMode of ['layer-pick','pick-item','brush','rect','erase'])
  assert.equal(vm.runInNewContext(guards,{canvasMode,e:{ctrlKey}}),false,canvasMode+' must reach its own dispatch');
 assert.equal(vm.runInNewContext(guards,{canvasMode:'layer-move',e:{ctrlKey}}),true);
 assert.equal(vm.runInNewContext(guards,{canvasMode:'eyedropper',e:{ctrlKey}}),ctrlKey);
}
function extract(name,next){return code.slice(code.indexOf('function '+name+'('),code.indexOf('function '+next+'('));}
const pc={width:4096,height:4096};
const base={id:'base',img:{},bbox:[0,0,4096,4096]},numbers={id:'numbers',img:{},bbox:[800,400,3100,4000]};
const sandbox={document:{getElementById:()=>pc},_psdLayers:[base,numbers],
 isPointOnLayerOpaque:layer=>layer===base,isLayerPickHelperLayer:()=>false,
 _layerHasOpaqueWithin:layer=>layer===numbers};
vm.createContext(sandbox);
vm.runInContext(extract('_isBaseLikeLayer','_layerHasOpaqueWithin')+extract('getTopmostVisibleLayerAtCanvasPoint','selectConnectedLayerPixelsAtPoint'),sandbox);
assert.equal(sandbox._isBaseLikeLayer(base),true);
assert.equal(sandbox._isBaseLikeLayer(numbers),false,'4096 artwork spread across a sheet is not a full-car base');
assert.equal(sandbox.getTopmostVisibleLayerAtCanvasPoint(2100,950,{editableOnly:true,snapRadius:26}),numbers);
assert.equal(sandbox.getTopmostVisibleLayerAtCanvasPoint(2100,950,{}),base,'ordinary exact-pixel callers retain their behavior');
numbers.visible=false;
assert.equal(sandbox.getTopmostVisibleLayerAtCanvasPoint(2100,950,{editableOnly:true,snapRadius:26}),base);
numbers.visible=true;numbers.locked=true;
assert.equal(sandbox.getTopmostVisibleLayerAtCanvasPoint(2100,950,{editableOnly:true,snapRadius:26}),base);
assert.equal(sandbox.getTopmostVisibleLayerAtCanvasPoint(2100,950,{editableOnly:true,includeLocked:true,snapRadius:26}),numbers);
const workflow=fs.readFileSync('js/canvas/tool-workflow.js','utf8');
const route=workflow.slice(workflow.indexOf('window.spbTransformObjectAt ='),workflow.indexOf('    const grab ='));
let activated=0,options;
const routeScope={window:{},selectConnectedLayerPixelsAtPoint(id,x,y,opts){options=opts;routeScope.window._spbLastPickedElementBbox={layerId:id};},
 activateLayerTransform(){activated++;return true;}};
vm.createContext(routeScope);vm.runInContext(route,routeScope);
assert.equal(routeScope.window.spbTransformObjectAt(numbers,10,20),true);
assert.equal(options.previewOnly,true); assert.equal(options.allowSnap,true); assert.equal(activated,1);
routeScope.selectConnectedLayerPixelsAtPoint=()=>{};
assert.equal(routeScope.window.spbTransformObjectAt(numbers,10,20),false); assert.equal(activated,1,'failed picks cannot become whole-layer transforms');
const alpha={width:15,height:13,data:new Uint8ClampedArray(15*13*4)};
alpha.data[(6*15+7)*4+3]=255;
const ringScope={_getLayerAlphaImageData:()=>alpha,getLayerCanvasOrigin:()=>({x:20,y:30})};
vm.createContext(ringScope);vm.runInContext(extract('_layerHasOpaqueWithin','getTopmostVisibleLayerAtCanvasPoint'),ringScope);
for(let y=26;y<48;y++)for(let x=16;x<40;x++)for(const radius of [0,1,4,9]){
 const hit=ringScope._layerHasOpaqueWithin({img:{},bbox:[20,30,35,43]},x,y,radius);
 assert.equal(hit,Math.max(Math.abs(x-27),Math.abs(y-36))<=radius);
}
console.log('Object picker: 4096 near miss finds Numbers; exact, hidden and locked targeting contracts pass.');
