const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const start=source.indexOf('function _paintOnLayerAt('),end=source.indexOf('\n// ─',start);
const queue=require('../js/canvas/layer/paint-preview-region.js').createQueue();
const calls=[],ctx={save(){},restore(){},fill(){},fillRect(){}};
const sandbox={_activeLayerCtx:ctx,_activeLayerCanvas:{width:4096,height:4096},
 _beginLayerDabSelectionPatch:()=>null,_finishLayerDabSelectionPatch(){},
 _getEraserMode:()=> 'brush',isLayerPaintSourceSpecial:()=>false,
 _createBrushFootprint:()=>({shape:'round',tracePath(){}}),
 _scheduleActiveLayerCompositePreview:r=>{calls.push(r);queue.add(r);}};
vm.createContext(sandbox);vm.runInContext(source.slice(start,end),sandbox);
for(const erase of [false,true]){
 calls.length=0;queue.clear();
 for(let x=100;x<=200;x+=5)sandbox._paintOnLayerAt(x,150,20,'#ff0000',1,1,erase);
 assert(calls.every(r=>r&&r.width<=45&&r.height<=45));
 const r=queue.consume();assert.deepEqual(r,{x:78,y:128,width:145,height:45});
 assert(r.width*r.height<4096*4096/1000,'ordinary Brush and Eraser must not request a whole image frame');
}
calls.length=0;sandbox._paintOnLayerAt(0,0,20,'#ff0000',1,1,false);
assert.deepEqual(JSON.parse(JSON.stringify(calls[0])),{x:0,y:0,width:23,height:23});
sandbox._beginLayerDabSelectionPatch=()=>false;calls.length=0;
assert.equal(sandbox._paintOnLayerAt(100,100,20,'#ff0000',1,1,false),false);assert.equal(calls.length,0);
console.log('Actual Brush/Eraser: small dirty union, antialias margin, edge clipping and rejected-selection no-op pass.');
