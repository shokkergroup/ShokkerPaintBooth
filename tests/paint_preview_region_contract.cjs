const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const api = require('../js/canvas/layer/paint-preview-region.js');
const q = api.createQueue();
q.add({x:8,y:9,width:20,height:10}); q.add({x:3,y:15,width:10,height:20});
assert.deepEqual(q.consume(),{x:3,y:9,width:25,height:26});assert.equal(q.consume(),null);
for(const invalid of [null,undefined,{x:NaN,y:0,width:10,height:10},{x:0,y:0,width:0,height:10}]) {
 q.add(invalid);q.add({x:1,y:1,width:2,height:2});assert.equal(q.consume(),null);
}
q.add({x:1,y:1,width:2,height:2});q.clear();assert.equal(q.consume(),null);
const source=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const start=source.indexOf('function _refreshActiveLayerCompositePreviewNow()');
const end=source.indexOf('// Layer undo:',start);
const helper=source.slice(start,end);
for(const effects of [undefined,{dropShadow:{enabled:true}},{dropShadow:{enabled:false}}]) {
 let pending=null,cancelled=0,drawn=0,events=[];
 const ctx={canvas:{width:100,height:100},save(){events.push('save');},restore(){events.push('restore');},beginPath(){},rect(...r){events.push(r);},clip(){events.push('clip');},clearRect(){events.push('clear');}};
 const active={id:2,effects},live={},editPixels={};
 const c={window:{SPBPaintPreviewRegion:api},_activePaintCompositeRegion:api.createQueue(),_activeLayerCompositePreviewRegion:api.createQueue(),_activeLayerCompositePreviewRaf:0,
  _psdLayers:[{id:1},active],_activeLayerPaintLayerId:2,_activeLayerCanvas:live,paintImageData:editPixels,
  document:{getElementById:()=>({width:100,height:100,getContext:()=>ctx})},
  _spbInspectLayerStack:()=>({ok:true}),_spbReportGroupFidelityFailure:()=>assert.fail('unexpected failure'),
  _spbCompositeLayerStack(context,layers,options){drawn++;assert.equal(context,ctx);assert.equal(options.sourceOverrideFor(active),live);assert.equal(options.sourceOverrideFor(layers[0]),null);return {ok:true};},
  requestAnimationFrame(fn){assert.equal(pending,null);pending=fn;return 1;},cancelAnimationFrame(){pending=null;cancelled++;}};
 vm.createContext(c);vm.runInContext(helper,c);
 c._scheduleActiveLayerCompositePreview();c._scheduleActiveLayerCompositePreview({x:1,y:2,width:3,height:4});
 let tick=pending;pending=null;tick();assert.equal(drawn,1);assert(!events.includes('clip'));
 events=[];c._scheduleActiveLayerCompositePreview({x:1,y:2,width:3,height:4});c._scheduleActiveLayerCompositePreview({x:3,y:4,width:5,height:6});
 tick=pending;pending=null;tick();assert.equal(drawn,2);assert.equal(events.includes('clip'),!effects?.dropShadow.enabled);
 if(events.includes('clip'))assert.deepEqual(events.find(Array.isArray),[1,2,7,8]);
 assert.equal(c.paintImageData,editPixels);assert.equal(events.at(-1),'restore');
 c._scheduleActiveLayerCompositePreview({x:1,y:2,width:3,height:4});c._cancelPendingActiveLayerCompositePreview();
 assert.equal(cancelled,1);assert.equal(c._activeLayerCompositePreviewRegion.consume(),null);
}
let restored=false;
assert.throws(()=>api.paint({canvas:{width:1,height:1},save(){},clearRect(){},restore(){restored=true;}},null,()=>{throw Error('draw failed');}),/draw failed/);
assert(restored);
console.log('Brush preview region: dirty union, full dominance, actual RAF/override/effect/cancel wiring and state restoration pass.');
