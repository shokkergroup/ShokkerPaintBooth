const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const api=require('../js/canvas/zone/source-layer-links.js');
const mask=Uint8Array.from([0,1,2,1]);
const linked={id:'z',sourceLayer:'psd_0',sourceLayers:['psd_0','psd_2'],base:'chrome',regionMask:mask,spatialMask:mask};
const unrelated={id:'unbound',base:'matte'};
const state={zones:[linked,unrelated],undo:[{label:'Scale',timestamp:123,snapshot:[{...linked,baseScale:1}]}],redo:[{label:'Scale',snapshot:[{...linked,baseScale:2}]}]};
const before=JSON.stringify(state),next=api.stage(state);
for(const zone of [next.zones[0],next.undo[0].snapshot[0],next.redo[0].snapshot[0]]) {
 assert.equal(zone.sourceLayer,null);assert.deepEqual(zone.sourceLayers,[]);
 assert.equal(zone.regionMask,mask);assert.equal(zone.spatialMask,mask);assert.equal(zone.base,'chrome');
}
assert.equal(next.zones[1],unrelated);assert.equal(JSON.stringify(state),before);
assert.equal(next.undo[0].label,'Scale');assert.equal(next.undo[0].timestamp,123);
const source=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const begin=source.indexOf("    if (opts.clearZoneSourceLayers !== false");
const end=source.indexOf('    try { if (typeof _resetLayerPaintFailToasts',begin);
const cleanup=source.slice(begin,end);
const zoneSource=fs.readFileSync('paint-booth-2-state-zones.js','utf8');
const replay=zoneSource.slice(zoneSource.indexOf('function undoZoneChange()'),zoneSource.indexOf('function jumpToUndoState('));
for(const keepLinks of [false,true]) {
 const c={window:{SPBSourceLayerLinks:api},opts:{clearZoneSourceLayers:!keepLinks},zones:state.zones,
  zoneUndoStack:state.undo.slice(),zoneRedoStack:state.redo.slice(),selectedZoneIndex:0,undoHistoryPointer:1,
  _cloneZoneState:zone=>({...zone,sourceLayers:zone.sourceLayers?.slice(),regionMask:null}),
  _ensureZoneShape:zone=>({...zone,sourceLayers:zone.sourceLayers?.slice()}),_cloneUint8ArrayLike:mask=>mask?.slice(),
  showToast(){},renderZones(){},_requestZoneLivePreview(){},renderUndoHistoryPanel(){}};
 const undoAlias=c.zoneUndoStack,redoAlias=c.zoneRedoStack;
 vm.createContext(c);vm.runInContext(cleanup+replay,c);
 assert.equal(c.zoneUndoStack,undoAlias);assert.equal(c.zoneRedoStack,redoAlias);
 for(const step of [()=>true,()=>c.undoZoneChange(),()=>c.redoZoneChange()]) {
  assert.equal(step(),true);assert.equal(c.zones[0].sourceLayer,keepLinks?'psd_0':null);
  assert.equal(c.zones[0].sourceLayers.length,keepLinks?2:0);assert.deepEqual(c.zones[0].regionMask,mask);
 }
}
console.log('Source Layer links: actual flat cleanup and recipe Undo/Redo detach singular/plural links, retain masks/settings/aliases and honor preserve option.');
