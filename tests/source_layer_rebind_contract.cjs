const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const api=require('../js/canvas/zone/source-layer-links.js');
const flatten=require('../js/canvas/layer/psd-import-safety.js').flattenLayerTree;
const leaf=name=>({name,has_pixels:true});
const old=flatten([leaf('Paint'),leaf('Number')],{width:4,height:4});
const next=flatten([leaf('Inserted'),leaf('Paint'),leaf('Number')],{width:4,height:4});
const mask=Uint8Array.from([0,255]);
const zone={id:'z',sourceLayer:'psd_0',sourceLayers:['psd_0','psd_1'],regionMask:mask,base:'chrome'};
const state={zones:[zone],undo:[{label:'Strength',snapshot:[zone]}],redo:[{snapshot:[zone]}]};
assert.equal(next.find(layer=>layer.id===zone.sourceLayer).name,'Inserted','negative control: positional binding points to wrong art');
const before=JSON.stringify(state),mapped=api.rebind(state,old,next);
for(const z of [mapped.zones[0],mapped.undo[0].snapshot[0],mapped.redo[0].snapshot[0]]) {
 assert.equal(z.sourceLayer,'psd_1');assert.deepEqual(z.sourceLayers,['psd_1','psd_2']);assert.equal(z.regionMask,mask);assert.equal(z.base,'chrome');
}
assert.equal(JSON.stringify(state),before);assert.equal(mapped.undo[0].label,'Strength');
const missing=api.rebind(state,old,flatten([leaf('Other')],{}));
assert(missing.zones[0].sourceLayers.every(id=>id.startsWith('spb_missing_layer:')));
assert.equal(missing.zones[0].sourceLayerBindings[missing.zones[0].sourceLayer].label,'Paint');
const recovered=api.rebind(missing,flatten([leaf('Other')],{}),next);
assert.deepEqual(recovered.zones[0].sourceLayers,['psd_1','psd_2']);
const duplicate=flatten([leaf('Paint'),leaf('Paint')],{});
assert(api.rebind(state,old,duplicate).zones[0].sourceLayer.startsWith('spb_missing_layer:'));
assert(api.rebind(state,duplicate,next).zones[0].sourceLayer.startsWith('spb_missing_layer:'));
const grouped=flatten([{name:'Left',children:[leaf('Logo')]},{name:'Right',children:[leaf('Logo')]}],{});
const reversed=flatten([{name:'Right',children:[leaf('Logo')]},{name:'Left',children:[leaf('Logo')]}],{});
assert.equal(api.rebind({zones:[{sourceLayer:'psd_0'}]},grouped,reversed).zones[0].sourceLayer,'psd_1');
const slashA=[{id:'a',pathParts:['A/B','C']}],slashB=[{id:'b',pathParts:['A','B/C']}];
assert(api.rebind({zones:[{sourceLayer:'a'}]},slashA,slashB).zones[0].sourceLayer.startsWith('spb_missing_layer:'));
assert.deepEqual(api.rebind(state,[],next).zones,state.zones,'saved initial-document bindings remain loadable');
const source=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const bridge=source.slice(source.indexOf('function _spbRebindSourceLayerLinks('),source.indexOf('function _spbSourcePixelHistoryState('));
const c={window:{SPBSourceLayerLinks:api},_psdLayers:old,zones:state.zones,zoneUndoStack:state.undo.slice(),zoneRedoStack:state.redo.slice()};
const undoAlias=c.zoneUndoStack;vm.createContext(c);vm.runInContext(bridge,c);c._spbRebindSourceLayerLinks(next);
assert.equal(c.zoneUndoStack,undoAlias);assert.equal(c.zones[0].sourceLayer,'psd_1');
const publication=source.indexOf('_spbRebindSourceLayerLinks(stagedLayers);');
assert(publication>source.indexOf('const liveComposite = _spbCompositeLayerStack(liveContext, stagedLayers)'));
assert(publication<source.indexOf('_psdLayers = stagedLayers;',publication));
console.log('Layer binding identity: real sequential-ID collision, reorder, missing/recovery, duplicate/group/slash ambiguity, history and publication bridge pass.');

// Execute the actual save/load property expressions through JSON, then reopen
// without a live predecessor against an inserted/reordered layer tree.
const zoneSource=fs.readFileSync('paint-booth-2-state-zones.js','utf8');
const expressions=[...zoneSource.matchAll(/sourceLayerBindings: (window\.SPBSourceLayerLinks\.snapshotBindings[^\n]+)/g)].map(m=>m[1].trim().replace(/,$/,''));
assert.equal(expressions.length,2);
const serialize=(z,layers,expr)=>vm.runInNewContext(expr,{window:{SPBSourceLayerLinks:api},z,_psdLayers:layers});
for(const original of [zone,missing.zones[0]]) {
 const save={...original,sourceLayerBindings:serialize(original,original===zone?old:[],expressions[0])};
 const parsed=JSON.parse(JSON.stringify(save));
 const restored={...parsed,sourceLayerBindings:serialize(parsed,[],expressions[1])};
 assert.deepEqual(api.rebind({zones:[restored]},[],next).zones[0].sourceLayers,['psd_1','psd_2']);
}
const savedDup={sourceLayer:'psd_0'};
savedDup.sourceLayerBindings=api.snapshotBindings(savedDup,duplicate);
assert(api.rebind({zones:[savedDup]},[],next).zones[0].sourceLayer.startsWith('spb_missing_layer:'));
const saved=api.snapshotBindings(zone,old);
saved.psd_0.key='wrong';
const normalized=api.snapshotBindings({...zone,sourceLayerBindings:saved},[]);
assert.equal(normalized.psd_0.key,'["Paint"]');
normalized.psd_0.parts[0]='Changed';assert.equal(saved.psd_0.parts[0],'Paint');
const html=fs.readFileSync('paint-booth-v2.html','utf8');
assert(html.indexOf('js/canvas/zone/source-layer-links.js')<html.indexOf('src="paint-booth-2-state-zones.js'));
console.log('Recipe/project JSON binding round-trip: live, missing/recovery, duplicate ambiguity, normalized independent metadata and load ordering pass.');
