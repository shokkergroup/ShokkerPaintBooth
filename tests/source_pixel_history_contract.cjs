const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const api=require('../js/canvas/source-pixel-history.js');
const fileCommit=require('../js/canvas/source-file-commit.js');
const source=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const slice=(a,b)=>source.slice(source.indexOf(a),source.indexOf(b,source.indexOf(a)));
const bridge=slice('function _spbSourcePixelHistoryState()', 'function _spbCommitSourceFile(');
const snapshot=slice('function _spbCaptureSourceDocumentState()', 'function _spbUpdateLoadedCanvasUi(');
const clearing=slice('function clearPSDDocumentState(', 'function getCurrentSourcePaintFile()');
function harness(legacy=false) {
 const old={data:new Uint8ClampedArray(16).fill(19),width:2,height:2,label:'Old paint'},zone={prevMask:new Uint8Array(4),sourceLayer:'old-layer',sourceLayers:['old-layer']};
 const canvas={width:2,height:2,getContext:()=>({getImageData:()=>({data:new Uint8ClampedArray(canvas.width*canvas.height*4).fill(73)})})};
 const c={SPBSourcePixelHistory:api,SPBSourceLayerLinks:require('../js/canvas/zone/source-layer-links.js'),_pixelUndoStack:[old],_pixelRedoStack:[old],_layerUndoStack:[old],_layerRedoStack:[old],
  _undoActionTrail:['zone-mask','pixel','zone-config','layer'],_redoActionTrail:['pixel','zone-mask','layer'],
  _undoHistoryView:[{kind:'zone-mask',label:'kept mask'},{kind:'pixel'},{kind:'zone-config',label:'kept config'},{kind:'layer'}],
  _colorBrushUndoSnapshot:old.data,zoneUndoStack:[{snapshot:[zone]}],zoneRedoStack:[{snapshot:[zone]}],undoStack:[zone],redoStack:[zone],zones:[{...zone,regionMask:zone.prevMask}],
  _psdData:null,_psdPath:null,_psdLayers:[],_psdLayersLoaded:false,_psdImportSafety:null,_selectedLayerId:null,
  _spbCommittedSourcePath:'old.tga',_spbCommittedSourceFingerprint:'old-hash',
  document:{getElementById:id=>id==='paintCanvas'?canvas:null},localStorage:{getItem:()=>null,removeItem(){},setItem(){}},
  _spbSnapshotCanvas:cv=>cv?{width:cv.width,height:cv.height}:null,
  _spbRestoreCanvasSnapshot(cv,s){if(cv&&s){cv.width=s.width;cv.height=s.height;}},_publishPSDDocumentState(){},
  historyRenders:0,renderUndoHistoryPanel(){c.historyRenders++;},console:{log(){},warn(){}}};
 c.window=c;vm.createContext(c);vm.runInContext(bridge+snapshot+(legacy?clearing.replace('_spbResetSourcePixelHistory();',''):clearing),c);
 return {c,canvas,old,zone};
}
// Negative control executes the old cleanup: a new source retains both old
// pixel stacks and the single-shot legacy restore, even after Layer cleanup.
{
 const {c,old}=harness(true);c.clearPSDDocumentState('new source');
 assert.equal(c._pixelUndoStack[0],old);assert.equal(c._pixelRedoStack[0],old);assert.equal(c._colorBrushUndoSnapshot,old.data);
}
for(const failed of [false,true]) {
 const {c,canvas,old,zone}=harness();
 const aliases={undo:c._pixelUndoStack,redo:c._pixelRedoStack,trail:c._undoActionTrail,view:c._undoHistoryView};
 const deps={canvas,settle(){},capture:c._spbCaptureSourceDocumentState,restore:c._spbRestoreSourceDocumentState,
  resizeMasks(){c.zoneUndoStack.splice(0,1,{snapshot:[]});c.zoneRedoStack.splice(0,1,{snapshot:[]});},publish(data){c.paintImageData=data;},clearPSD(){c.clearPSDDocumentState('new source');if(failed)throw Error('post-cleanup fault');}};
 if(failed)assert.throws(()=>fileCommit.run(deps,4,4,()=>{}),/post-cleanup fault/);
 else fileCommit.run(deps,4,4,()=>{});
 assert.equal(c._pixelUndoStack,aliases.undo);assert.equal(c._pixelRedoStack,aliases.redo);assert.equal(c._undoActionTrail,aliases.trail);assert.equal(c._undoHistoryView,aliases.view);
 assert.equal(c.undoStack[0],zone);assert.equal(c.redoStack[0],zone);
 assert.equal(c.historyRenders,failed?2:1);
 if(failed) {
  assert.equal(c._pixelUndoStack[0],old);assert.equal(c._pixelRedoStack[0],old);assert.equal(c._layerUndoStack[0],old);
  assert.equal(c.zoneUndoStack[0].snapshot[0],zone);assert.equal(c.zoneRedoStack[0].snapshot[0],zone);assert.equal(c.zones[0].sourceLayer,'old-layer');assert.equal(c.zones[0].sourceLayers[0],'old-layer');
  assert.equal(c._colorBrushUndoSnapshot,old.data);assert.equal(canvas.width,2);
  assert.deepEqual(Array.from(c._undoActionTrail),['zone-mask','pixel','zone-config','layer']);
 } else {
  assert.equal(c._pixelUndoStack.length,0);assert.equal(c._pixelRedoStack.length,0);assert.equal(c._layerUndoStack.length,0);
  assert.equal(c._colorBrushUndoSnapshot,null);assert.equal(canvas.width,4);
  assert.deepEqual(Array.from(c._undoActionTrail),['zone-mask','zone-config']);assert.deepEqual(Array.from(c._redoActionTrail),['zone-mask']);
  assert.deepEqual(Array.from(c._undoHistoryView,e=>e.label),['kept mask','kept config']);
 }
}
const psd=slice('// Destructive outgoing-session cleanup starts only after commit,','function _spbInspectLayerStack(');
assert(psd.indexOf('_spbResetSourcePixelHistory();')>psd.indexOf('_layerRedoStack.length = 0;'));
console.log('Source history: old-code negative control, real flat commit/rollback, stable aliases, retained Zone chronology and PSD cleanup hook pass.');
