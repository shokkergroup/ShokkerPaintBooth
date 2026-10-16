'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
const w={console,document:{readyState:'loading',addEventListener(){},querySelector(){return null},getElementById(){return null}},localStorage:{getItem(){return null}},setTimeout(){},setInterval(){},_psdLayers:[{id:'sponsor',name:'Sponsor',groupName:'Art',visible:true,spbMaterial:{v:1,preset:'matte'}},{id:'number',name:'Number',visible:false,spbMaterial:{v:1,preset:'carbon',keep:true,edge:{preset:'chrome',width:3},lip:20}}]};
w.window=w;vm.createContext(w);
for(const file of ['js/rev/layermat/layermat-core.js','mcp/chatgpt/editor-capabilities.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),w,{filename:file});
const before=JSON.stringify(w._psdLayers),api=w.SpbEditorCapabilities;
// Execute the generated state() caller too: promotion filtering once silently
// dropped the new field even though the standalone reader/context tests passed.
const pro=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8');
const stateStart=pro.indexOf('    function state() {'),stateEnd=pro.indexOf('    // ------------------------------------------------------------------ tools',stateStart);
assert.ok(stateStart>=0&&stateEnd>stateStart);
Object.assign(w,{Z:{paintColours:()=>[],zonesForModel:()=>[]},layersInfo:()=>w._psdLayers,carForModel:()=>null,memNotes:()=>({buyer:[],this_car:[]}),selectedZoneIndex:-1,_skipParts:false,RECENT:[],recolZones:()=>({n:0})});
vm.runInContext(pro.slice(stateStart,stateEnd),w);
assert.equal(w.state().editor_capabilities.layer_materials.assigned_count,2,'Actual generated state caller exposes the installed feature');
w.SPBRevLayerMat.assign=()=>{throw Error('A reader may not assign');};
let s=api.read();assert.equal(s.layer_materials.enabled,true);assert.equal(s.layer_materials.assigned_count,2);assert.equal(s.layer_materials.assignments[1].visible,false);assert.match(s.layer_materials.assignments[1].description,/keep art colour/);assert.equal(s.layer_materials.presets.length,7);
let q='What materials are assigned to my layers?';assert.match(api.answer(q).answer.text,/Art \/ Sponsor \[sponsor\]: Matte Vinyl/);assert.equal(api.answer(q).answer.actions.length,0);
assert.equal(JSON.stringify(w._psdLayers),before);s.layer_materials.assignments[0].material.preset='chrome';assert.equal(api.read().layer_materials.assignments[0].material.preset,'matte');
w.SPB_REV_LAYERMAT_OFF=true;assert.equal(api.read().layer_materials.enabled,false);assert.match(api.answer(q).answer.text,/currently disabled/);assert.equal(api.read().layer_materials.assigned_count,2);w.SPB_REV_LAYERMAT_OFF=false;
w._psdLayers[0].spbMaterial={bad:true};assert.match(api.answer(q).answer.text,/inventory is incomplete/);w._psdLayers=[];assert.match(api.answer(q).answer.text,/No live layers/);
w._nuqPreviewComposite=()=>{throw Error('Read must not composite');};w._nuqOff=()=>false;assert.equal(api.read().preview.guide_filter_enabled,true);assert.match(api.answer('Why are guides missing from Live Preview?').answer.text,/fallback|fall back/);w._nuqOff=()=>true;assert.equal(api.read().preview.guide_filter_enabled,false);
for(const q of ['Assign matte Layer Materials to my sponsor','Can you assign Layer Materials to my sponsor?','What are Layer Materials? Then make my car red','Explain Layer Materials and apply chrome to my numbers','Why is Live Preview different? Hide the Mask'])assert.equal(api.answer(q),null,q);
// The actual Offline route must reach the common reader, without executable steps.
for(const file of ['spb-offline-builder.js','spb-offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'candidates',file),'utf8'),w,{filename:file});
const answer=w.SpbOfflineAnswer.route('How do Layer Materials work?',{layers:[],palette:[],zoneColours:[]});assert.equal(answer.cls,'ANSWER');assert.equal(answer.answer.id,'assistant.live_editor_capabilities');assert.ok(!answer.steps||!answer.steps.length);
const sendStart=pro.indexOf('    function send(text, o) {'),nextFunction=pro.slice(sendStart+1).match(/^    function \w+\(/m),sendCode=pro.slice(sendStart,sendStart+1+nextFunction.index);
const cards=[],input={value:q},drawOrder=[];Object.assign(w,{_busy:false,_log:[],_panel:{setAttribute(){},querySelectorAll:()=>[],querySelector:s=>s==='.spb-pai-input'?input:null},SpbAiConnect:{relaying:()=>false},SpbDesignIntent:require('./design-intent.js'),SpbOfflineBuilder:{offlineMode:()=>true,state:()=>({}),showAnswer:p=>cards.push(p)},SpbPbn:{draw:()=>{assert.equal(drawOrder.at(-1),'finish');drawOrder.push('suggestions');}},finish:r=>{drawOrder.push('finish');return r;}});
const composerStart=pro.indexOf('    var _composerFinishing = 0'),composerEnd=pro.indexOf('    function finish(',composerStart);
vm.runInContext(pro.slice(composerStart,composerEnd),w);
Object.assign(w,{zones:[],SpbNamedPatternRefinement:require('./named-pattern-refinement.js')});
vm.runInContext(pro.slice(pro.indexOf('    var _patternAdviceSnapshot = null;'),pro.indexOf('    function offlineNamedZoneMaterial(parsed) {')),w);
vm.runInContext(sendCode.replace('// CAR-KNOWLEDGE:',"throw Error('legacy route'); // CAR-KNOWLEDGE:"),w);
for(const question of ['What materials are assigned to my layers? Do not change anything.','Why are guides missing from Live Preview?','What material is on Sponsors?']){const r=w.send(question);assert.equal(cards.at(-1).answer.id,'assistant.live_editor_capabilities');assert.equal(r.queue.length,0);assert.equal(r.tools.length,0);assert.equal(input.value,'');assert.equal(r.text,cards.at(-1).answer.text);assert.equal(cards.at(-1).in_chat,true);}
assert.deepEqual(drawOrder,['finish','suggestions','finish','suggestions','finish','suggestions'],'Suggestion visibility follows the completed answer redraw');
// Follow-ups reuse only this document's immediately preceding factual card.
let topicState={},epoch=7;
w.SpbConversationScope={observe(){},stamp:()=>epoch,current:s=>s===epoch};
w.SpbOfflineBuilder.state=()=>topicState;
w.SpbOfflineBuilder.showAnswer=(r,text)=>{topicState={answer:r,text};cards.push(r);};
w.send('What is Spec Doctor?');
const follow=w.send('Where is that?');assert.equal(follow.queue.length,0);assert.equal(cards.at(-1).answer.editor_topic,'doctor');assert.match(cards.at(-1).answer.title,/Find/);
w._log.push({role:'user',text:'Which colour goes with blue?'},{role:'ai',text:'Gold'});
assert.throws(()=>w.send('Where is that?'),/legacy route/,'Unrelated turn cannot resurrect the lingering card');
w.send('How does Edge Bleed work?');epoch++;
assert.throws(()=>w.send('How do I use it?'),/legacy route/,'Changed document invalidates the topic');
w.send('What is Spec Doctor and Edge Bleed?');
assert.throws(()=>w.send('Where is that?'),/legacy route/,'Two tool topics remain ambiguous');
w.send('What is Spec Doctor?');
assert.throws(()=>w.send('Where is that? Run it now'),/legacy route/,'Follow-up cannot swallow an edit');
w.SpbAiConnect.relaying=()=>true;assert.throws(()=>w.send(q),/legacy route/,'Online questions keep their provider route');w.SpbAiConnect.relaying=()=>false;
assert.throws(()=>w.send('What are Layer Materials? Then make my car red'),/legacy route/,'Mixed edit tail stays with the full router');
const context=require('./assistant-context.cjs');
(async()=>{const live=api.read();const packet=await context.build({query:q,include_paint:true},{history:async()=>({turns:[]}),tools:()=>[],call:async name=>({content:[{type:'text',text:JSON.stringify(name==='spb_get_state'?{editor_capabilities:live}:{})}]})});assert.deepEqual(packet.editor_capabilities,JSON.parse(JSON.stringify(live)));assert.equal(packet.capabilities.length,0,'Installed editor feature does not invent a write tool');console.log(JSON.stringify({pass:true,actual_native_material_reader:true,offline_route:true,MCP_context:true,read_only:true,disabled_and_unknown_cases:true,mixed_requests_not_absorbed:true}));})().catch(e=>{console.error(e);process.exitCode=1});
