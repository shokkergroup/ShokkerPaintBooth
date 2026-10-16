'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../../..'),L=require('./layer-reading.js');
const receipt=JSON.parse(fs.readFileSync(path.join(root,'_codex_mcp_work/chatgpt-dev/59910/paint-official-arca-import-2026-10-09T22-26-30-056Z.json'),'utf8'));
const observed=JSON.parse(receipt.calls[0].text).layers;
const layerRows=observed.map((r,i)=>({...r,id:'real-'+i,groupName:r.group,visible:!r.hidden,img:{width:2048,height:2048}}));
function runtime(file,module){
 const w={console,Set,Map,Date,Uint8Array,Promise,document:{readyState:'loading',getElementById:()=>null,addEventListener(){}},localStorage:{getItem:()=>null,setItem(){}},_psdLayers:layerRows.map(r=>({...r})),setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},clearInterval(){},addEventListener(){},SPBSourceLoadTransaction:{getGeneration:()=>1}};w.window=w;vm.createContext(w);
 if(module)vm.runInContext(fs.readFileSync(path.join(__dirname,'layer-reading.js'),'utf8'),w);
 vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),w);return w;
}
const old=runtime('js/spb-pro-carmap.js',false),w=runtime('mcp/chatgpt/candidates/spb-pro-carmap.js',true);
assert.equal(old.SpbProCar.roles().filter(r=>r.role==='body paint').length,4,'Real imported state reproduces the three spec Base Paint false positives');
let roles=w.SpbProCar.roles();assert.equal(roles.filter(r=>r.role==='body paint').length,1);assert.equal(roles.filter(r=>/^spec map/.test(r.role)).length,6);
w.SPB_CX3_OFF=true;assert.equal(w.SpbProCar.roles().filter(r=>r.role==='body paint').length,4,'Promoted owner role switch preserves legacy behavior and retires cache');w.SPB_CX3_OFF=false;assert.equal(w.SpbProCar.roles().filter(r=>r.role==='body paint').length,1);
assert.equal(roles.filter(r=>/^spec map/.test(r.role)&&r.role==='body paint').length,0);
assert.equal(roles.find(r=>r.group==='Custom Spec Map'&&r.name==='Alpha').role,'spec map alpha (purpose unverified)');
const body=w._psdLayers.find(r=>r.name==='Base Paint'&&r.groupName==='Paintable Area');body.groupName='Custom Spec Map / Red Channel Metallic';
assert.equal(w.SpbProCar.roles().find(r=>r.id===body.id).role,'spec map (metallic)','Reparenting must retire the role cache without changing geometry names');
const sheet=L.read(observed);assert.equal(sheet.spec_label_records,6);assert.ok(sheet.duplicate_names.find(d=>d.name==='Base Paint'&&d.occurrences===4));assert.equal(sheet.can_target_panels,false);assert.equal(sheet.actions.length,0);
const a=L.answer('What do the Base Paint layers in my template spec groups mean?',observed);assert.ok(a);assert.match(a.text,/not the livery body colour/);assert.match(a.text,/Names repeat/);assert.equal(a.actions.length,0);assert.equal(a.live_context,true);
assert.equal(L.answer('Make all layers red',observed),null);assert.equal(L.answer('What colour palette should I use?',observed),null);assert.equal(L.classify({name:'Body',group:'Special art'}),null);
assert.equal(L.classify({name:'Spec Racer logo',group:'Sponsors'}),null,'A car/brand word Spec does not declare a material map');assert.equal(L.classify({name:'Base Paint',group:'Spec / Metallic'}).channel,'metallic');
assert.equal(L.classify({name:'Alpha',group:'Paintable Area'}).kind,'alpha');
const bounded=L.read(Array.from({length:1000},(_,i)=>({name:'Base Paint',group:'Custom Spec Map / Red Channel Metallic / '+i})));assert.equal(bounded.observed_records,300);assert.equal(bounded.records_omitted,700);assert.equal(bounded.groups.length,12);
const partial=L.answer('Explain my template groups',Array.from({length:7},(_,i)=>({name:'Alpha',group:'Paintable Area '+i})));
assert.match(partial.text,/additional groups/);assert.doesNotMatch(partial.text,/control-pixel/);assert.equal(partial.actions.length,0);
const knowledge=JSON.parse(fs.readFileSync(path.join(__dirname,'build/knowledge.json'),'utf8')),K=require('./core.js');
let inspected=0;
for(const car of knowledge.cars)for(const m of car.template_metadata){
 const guide=L.reference(m,'Explain template spec layers');assert.ok(guide);assert.equal(guide.current_file_verified,false);assert.equal(guide.can_target_panels,false);assert.equal(guide.actions.length,0);
 assert.equal(guide.observed_records,m.layer_labels.filter(p=>!m.layer_groups.includes(p)).length,'Group nodes must not be counted as pixel layers');inspected++;
}
const arca=knowledge.cars.find(c=>c.id==='stockcars2-arcachevy25');
const reference=K.lookup({car_id:arca.id,query:'Explain metallic template layers'},knowledge);
assert.ok(reference.car.template_layer_guides.length);assert.equal(reference.car.template_layer_guides[0].current_file_verified,false);
assert.ok(JSON.stringify(reference).length<28000,'Layer interpretation stays a bounded reference packet');
assert.equal(L.answerReference('Explain template groups',{layer_labels:['Spec / Base Paint']}),null,'An old reference without group-node metadata must not guess layer records');
// Exercise the actual Offline route, not just the new formatter.
const route=runtime('mcp/chatgpt/candidates/spb-pro-carmap.js',true);route.SpbTemplateIdentity={read:()=>({})};
for(const file of ['mcp/chatgpt/design-intent.js','mcp/chatgpt/car-knowledge/core.js','mcp/chatgpt/car-knowledge/offline-answer.js','js/spb-encyclopedia-data.js','js/spb-enc-search.js','mcp/chatgpt/candidates/spb-offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),route);
(async()=>{
 await route.SpbOfflineAnswer.load(async name=>{try{return JSON.parse(fs.readFileSync(name==='cars.json'?path.join(__dirname,'build/cars.json'):path.join(root,'data/encyclopedia',name),'utf8'));}catch{return null;}});
 const answer=route.SpbOfflineAnswer.route('What do the Base Paint layers in my template spec groups mean?',{layers:route.SpbProCar.roles()});
 assert.equal(answer.cls,'ANSWER');assert.equal(answer.answer.live_context,true);assert.equal(answer.answer.actions.length,0);assert.match(answer.answer.text,/spec map/);
 const boundedAnswer=route.SpbOfflineAnswer.route('What do the Base Paint layers in my template spec groups mean? Do not change anything.',{layers:route.SpbProCar.roles()});
 assert.equal(boundedAnswer.answer.id,'assistant.template_layers','No-edit wording must not replace a factual layer question with generic design advice');assert.equal(boundedAnswer.answer.actions.length,0);
 for(const question of ['Show my layers. Do not change anything.','List loaded layers','Please display my groups','Show my layers']){
  const inventory=route.SpbOfflineAnswer.route(question,{layers:route.SpbProCar.roles()});
  assert.equal(inventory.answer.id,'assistant.template_layers');assert.equal(inventory.answer.title,'Your loaded layers');assert.equal(inventory.answer.actions.length,0);assert.match(inventory.answer.text,/42 loaded layer records/);assert.match(inventory.answer.text,/Paintable Area/);
 }
 for(const question of ['What does roughness mean in my template?','What does the blue channel do in my spec map?','Explain my template’s metallic channel.']){
  const material=route.SpbOfflineAnswer.route(question,{layers:route.SpbProCar.roles()});assert.equal(material.answer.id,'assistant.template_layers');assert.equal(material.answer.live_context,true);assert.equal(material.answer.actions.length,0);assert.match(material.answer.text,/exported spec-map values/);
 }
 const named=route.SpbOfflineAnswer.route('What do my Ferrari 296 GT3 template spec layers mean?',{layers:route.SpbProCar.roles()});assert.notEqual(named.answer&&named.answer.live_context,true,'A named different car must not receive the open ARCA layer sheet');
 const arcaQuestion='What do the '+arca.name+' template spec layers mean?';
 const arcaHits=route.SpbOfflineAnswer.search(arcaQuestion,3),namedReference=route.SpbOfflineAnswer.answerOf(arcaHits[0],arcaQuestion);
 assert.equal(namedReference.reference_context,true);assert.equal(namedReference.live_context,false);assert.equal(namedReference.actions.length,0);assert.match(namedReference.text,/do not verify your loaded file/);assert.ok(namedReference.sources.length);
 assert.ok(namedReference.sources.some(s=>s.url==='https://www.iracing.com/custom-paint-textures/'));assert.ok(namedReference.sources.some(s=>/31000168823/.test(s.url)));assert.ok(namedReference.sources.some(s=>!s.url.includes('custom-paint-textures')&&!s.url.includes('31000168823')),'Template evidence citation survives alongside general material sources');
 assert.equal(K.lookup({car_id:'legends-ford34c-rookie'},knowledge).car.status,'retired');
 const context=await require('../assistant-context.cjs').build({query:'Explain my template spec layers',include_paint:true},{history:async()=>({turns:[]}),tools:()=>[],call:async name=>({content:[{type:'text',text:JSON.stringify(name==='spb_get_state'?{layers:observed}:name==='spb_status'?{}:{articles:[]})}]})});
 assert.equal(context.template_layers.spec_label_records,6);assert.equal(context.template_layers.can_target_panels,false);
 console.log(JSON.stringify({pass:true,actual_imported_layers:observed.length,baseline_body_roles:4,candidate_body_roles:1,spec_records:6,offline_actions:0,cache_reparenting:'pass',mcp_context:'pass',reference_documents:inspected,named_reference:'pass'}));
})().catch(e=>{console.error(e);process.exitCode=1;});
