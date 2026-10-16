'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const w={document:{readyState:'loading',addEventListener(){},getElementById(){return null},querySelector(){return null}},localStorage:{getItem(){return null}},setInterval(){},setTimeout(){},console,
 _psdLayers:[{id:'s1',name:'Sponsors',groupName:'Artwork',visible:true},{id:'s2',name:'Sponsors',groupName:'Rear',visible:true,groupChain:[{ownVisible:false}],spbMaterial:{v:1,preset:'matte'}},{id:'b',name:'Body',spbMaterial:{v:1,preset:'chrome'}}],_selectedLayerIds:new Set(['b'])};
w.window=w;vm.createContext(w);
for(const f of ['../../js/rev/layermat/layermat-core.js','editor-capabilities.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,f),'utf8'),w,{filename:f});
const api=w.SpbEditorCapabilities,before=JSON.stringify(w._psdLayers);
w.SPBRevLayerMat.assign=()=>{throw Error('Read may not assign');};
let a=api.answer('What material is on Sponsors? Explain only.');
assert.equal(a.answer.named_layer_materials.ambiguous,true);assert.match(a.answer.text,/Artwork \/ Sponsors \[s1\]: None/);assert.match(a.answer.text,/Rear \/ Sponsors \[s2\]: Matte Vinyl \(hidden/);assert.match(a.answer.text,/specify the full group path or exact ID/);assert.ok(!a.answer.text.includes('Body: Chrome'));
for(const q of ['What material is on Artwork / Sponsors?','Which material is s1 using?','What Layer Material does "Artwork / Sponsors" have?']){
 a=api.answer(q);assert.equal(a.answer.named_layer_materials.records.length,1,q);assert.equal(a.answer.named_layer_materials.records[0].id,'s1');assert.match(a.answer.text,/zones or imported spec/);assert.equal(a.answer.actions.length,0);
}
a=api.answer('What material is on Body?');assert.match(a.answer.text,/Chrome Foil/);assert.match(a.answer.text,/visibility unknown/);assert.ok(!a.answer.text.includes('(hidden'));
a=api.answer('What material is on Missing?');assert.match(a.answer.text,/cannot find an exact loaded layer/);assert.match(a.answer.text,/not substituted the selected layer/);
assert.equal(api.read('How does Spec Doctor work?').layer_materials.named_layers,null);
for(const q of ['What material is on Sponsors? Then make it chrome.','What material is on Sponsors and apply chrome?','What material is on Sponsors? Export it now.'])assert.equal(api.answer(q),null,q);
w.SPB_REV_LAYERMAT_OFF=true;assert.match(api.answer('What material is on Body?').answer.text,/currently disabled/);w.SPB_REV_LAYERMAT_OFF=false;
w._psdLayers[0].spbMaterial={bad:true};assert.match(api.answer('What material is on s1?').answer.text,/could not be read/);delete w._psdLayers[0].spbMaterial;
w._psdLayers.push({id:'s1',name:'Other'});a=api.answer('What material is on Artwork / Sponsors?');assert.equal(a.answer.named_layer_materials.records.length,0);assert.equal(a.answer.named_layer_materials.unresolved_ids[0],'s1');w._psdLayers.pop();
w._psdLayers.push({id:7,name:'Number A'},{id:'7',name:'Number B'});assert.equal(api.read('What material is on Number A?').layer_materials.named_layers.records.length,0);w._psdLayers.splice(-2);
w._psdLayers.push({id:'x'.repeat(121),name:'Long ID'});assert.equal(api.read('What material is on Long ID?').layer_materials.named_layers.records.length,0);w._psdLayers.pop();
assert.equal(JSON.stringify(w._psdLayers),before);
// Generated state caller receives the question, rather than an unqualified inventory.
const pro=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8');
const start=pro.indexOf('    function state() {'),end=pro.indexOf('    // ------------------------------------------------------------------ tools',start);
Object.assign(w,{Z:{paintColours:()=>[],zonesForModel:()=>[]},layersInfo:()=>w._psdLayers,carForModel:()=>null,memNotes:()=>({buyer:[],this_car:[]}),selectedZoneIndex:-1,_skipParts:false,RECENT:[],recolZones:()=>({n:0})});
vm.runInContext(pro.slice(start,end),w);assert.equal(w.state('What material is on Sponsors?').editor_capabilities.layer_materials.named_layers.matched_layers,2);
assert.match(pro,/handler: function \(a\) \{ var s = state\(a && a.editor_query\)/);
for(const f of ['spb-offline-builder.js','spb-offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'candidates',f),'utf8'),w);
assert.equal(w.SpbOfflineAnswer.route('What material is on Sponsors?',{}).answer.named_layer_materials.matched_layers,2);
// A new document must replace all previous observations.
w._psdLayers=[{id:'new',name:'Sponsors',visible:true,spbMaterial:{v:1,preset:'carbon'}}];a=api.answer('What material is on Sponsors?');assert.equal(a.answer.named_layer_materials.records[0].id,'new');assert.match(a.answer.text,/Carbon/);assert.ok(!a.answer.text.includes('Matte Vinyl'));
w._psdLayers=Array.from({length:1001},(_,i)=>({id:String(i),name:i?'Other':'Sponsors',visible:true}));a=api.answer('What material is on Sponsors?');assert.equal(a.answer.named_layer_materials.records.length,0);assert.equal(a.answer.named_layer_materials.unread_layers,1);assert.match(a.answer.text,/incomplete/);
w._psdLayers=Array.from({length:20},(_,i)=>({id:String(i),name:'Sponsors',groupName:'Group'+i,visible:true}));a=api.answer('What material is on Sponsors?');assert.equal(a.answer.named_layer_materials.records.length,12);assert.equal(a.answer.named_layer_materials.omitted_matches,8);
const context=require('./assistant-context.cjs');
(async()=>{let called;const q='What material is on Sponsors?';const packet=await context.build({query:q,include_paint:true},{history:async()=>({turns:[]}),tools:()=>[],call:async(name,args)=>{if(name==='spb_get_state')called=args;return {content:[{type:'text',text:JSON.stringify(name==='spb_get_state'?{editor_capabilities:w.state(q).editor_capabilities}:{})}]};}});assert.equal(called.editor_query,q);assert.equal(packet.editor_capabilities.layer_materials.named_layers.matched_layers,20);console.log(JSON.stringify({pass:true,actual_owner_material_core:true,generated_state_and_offline_route:true,MCP_question_forwarding:true,duplicates_hidden_ancestors_unknown_visibility:true,unreadable_bounded_and_changed_document:true,zero_mutations:true}));})().catch(e=>{console.error(e);process.exitCode=1;});
