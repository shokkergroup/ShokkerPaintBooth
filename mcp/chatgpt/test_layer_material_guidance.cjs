'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const w={document:{readyState:'loading',addEventListener(){},getElementById(){return null;},querySelector(){return null;}},localStorage:{getItem(){return null;}},setInterval(){},setTimeout(){},console,
 _psdLayers:[{id:'s',name:'Sponsors',groupName:'Artwork',visible:true},{id:'b',name:'Body',visible:true,spbMaterial:{v:1,preset:'chrome'}},{id:'n',name:'Numbers',visible:false,locked:true,spbMaterial:{v:1,preset:'matte'}}],_selectedLayerIds:new Set(['s'])};
w.window=w;vm.createContext(w);
for(const f of ['../../js/rev/layermat/layermat-core.js','editor-capabilities.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,f),'utf8'),w,{filename:f});
const api=w.SpbEditorCapabilities,before=JSON.stringify(w._psdLayers);
w.SPBRevLayerMat.assign=()=>{throw Error('Reader must not assign');};
let s=api.read().layer_materials;
assert.equal(s.selection.known,true);assert.equal(s.selection.records.length,1);assert.equal(s.selection.records[0].name,'Sponsors');assert.equal(s.selection.records[0].state,'none');
let a=api.answer('What material is on the selected layer? Explain only.');
assert.match(a.answer.text,/Sponsors: None \(zones decide\)/);assert.match(a.answer.text,/zones or imported spec/);assert.ok(!a.answer.text.includes('[s]'));assert.deepEqual(Array.from(a.answer.actions),[]);
for(const q of ['Can I keep my sponsors matte while the body stays chrome? Please explain only.','How do I keep the logos chrome without changing the matte body?']){
 a=api.answer(q);assert.equal(a.answer.editor_topic,'material');assert.match(a.answer.text,/Matte Vinyl/);assert.match(a.answer.text,/Chrome Foil/);assert.match(a.answer.text,/leave the body settings alone/);assert.match(a.answer.text,/does not confirm that the body is currently chrome/);assert.ok(!a.answer.text.includes('Spec Doctor'));assert.deepEqual(Array.from(a.answer.actions),[]);
}
assert.equal(api.answer('Can you keep my sponsors matte while the body stays chrome?'),null);
for(const q of ['Make my sponsors matte while the body stays chrome.','What material is on the selected layer? Then make it chrome.','How do I keep sponsors matte? Apply it now.'])assert.equal(api.answer(q),null,q);
// A symptom remains diagnostic; the new design-choice route does not hide it.
w.SPBRevDoctor={off:()=>false};assert.match(api.answer('Why are my sponsors chrome while the body is metallic?').answer.text,/Spec Doctor/);
w._selectedLayerIds=new Set(['b','n']);s=api.read().layer_materials;assert.equal(s.selection.records[0].description,'Chrome Foil');assert.equal(s.selection.records[1].visible,false);
a=api.answer('Which material is on my selected layers?');assert.match(a.answer.text,/Body: Chrome Foil/);assert.match(a.answer.text,/Numbers: Matte Vinyl \(hidden; no material contribution\) \(locked\)/);
s.selection.records[0].material.preset='matte';assert.equal(api.read().layer_materials.selection.records[0].material.preset,'chrome');
w.SPB_REV_LAYERMAT_OFF=true;assert.match(api.answer('Can I keep sponsors matte while the body stays chrome?').answer.text,/currently disabled/);assert.ok(!api.answer('Can I keep sponsors matte while the body stays chrome?').answer.text.includes('Give the actual sponsor'));w.SPB_REV_LAYERMAT_OFF=false;
w._selectedLayerIds=new Set(['missing']);assert.equal(api.read().layer_materials.selection.unresolved_ids.length,1);assert.match(api.answer('What material is on the selected layer?').answer.text,/incomplete/);
w._selectedLayerIds=new Set(['s']);w._psdLayers.push({id:'s',name:'Duplicate'});assert.equal(api.read().layer_materials.selection.records.length,0);w._psdLayers.pop();
w._psdLayers[0].spbMaterial={bad:true};assert.match(api.answer('What material is on the selected layer?').answer.text,/could not be read/);delete w._psdLayers[0].spbMaterial;
w._selectedLayerIds=new Set();assert.match(api.answer('What material is on the selected layer?').answer.text,/No layer is selected/);
delete w._selectedLayerIds;assert.equal(api.read().layer_materials.selection.known,false);assert.match(api.answer('What material is on the selected layer?').answer.text,/selected layer could not be read/);
assert.equal(JSON.stringify(w._psdLayers),before);
console.log(JSON.stringify({pass:true,actual_owner_material_core:true,read_only_selection:true,natural_design_choice:true,symptom_stays_diagnostic:true,mixed_edits_not_absorbed:true,disabled_missing_duplicate_unreadable_selection:true}));
