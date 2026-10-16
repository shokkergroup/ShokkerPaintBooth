'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'../../..'),L=require('./layer-reading.js');
const native=JSON.parse(fs.readFileSync(path.join(root,'_codex_mcp_work/chatgpt-dev/59910/source-bound-page-2026-10-11T01-04-33-724Z.json'),'utf8'));
// Use actual page records, not invented duplicate layer names.
const rows=native.roundtrip.initial_fields.layers;
assert.equal(rows.length,42);
const before=JSON.stringify(rows);
for(const q of ['What does Base Paint do?','Which Base Paint should I use for body colour?','Explain “Base Paint”.','Why are there four Base Paint layers?']){
 const a=L.answer(q,rows);assert.ok(a,q);assert.equal(a.live_context,true);assert.equal(a.actions.length,0);
 assert.equal(a.layer_choices.observed_matches,4);assert.deepEqual(a.layer_choices.choices.map(c=>c.id),['psd_0','psd_37','psd_38','psd_40']);
 assert.equal(a.layer_choices.choices.filter(c=>c.kind==='artwork').length,1);assert.equal(a.layer_choices.choices.filter(c=>c.kind==='spec').length,3);
 assert.match(a.chat_summary,/Paintable Area \/ Base Paint/);assert.match(a.text,/not the livery body colour/);assert.match(a.text,/Names repeat/);
 assert.equal(a.layer_choices.choices.find(c=>c.id==='psd_37').visible,false);assert.equal(a.layer_choices.choices.find(c=>c.id==='psd_0').visible,null,'Absent visibility is unknown, not inferred shown');
}
for(const q of ['What does Paintable Area / Base Paint do?','What does psd_0 do?']){const a=L.answer(q,rows);assert.equal(a.layer_choices.observed_matches,1);assert.equal(a.layer_choices.choices[0].id,'psd_0');}
const spec=L.answer('Explain Custom Spec Map / Red Channel Metallic / Base Paint',rows);assert.equal(spec.layer_choices.observed_matches,1);assert.equal(spec.layer_choices.choices[0].channel,'metallic');assert.match(spec.text,/0 is nonmetal/);assert.doesNotMatch(spec.text,/artwork candidate/);
for(const q of ['Make Base Paint red','What does Base Paint do? Apply gold.','Explain Base Paint; please render it.','Which Base Paint is artwork and could you hide it?','Explain Base Paint then add a logo','What does Base Paint do and colour it blue'])assert.equal(L.answer(q,rows),null,q);
for(const q of ['How do I move Base Paint?','What colour is Base Paint?'])assert.equal(L.focusedQuestion(q,rows),false,q);
const unknown=L.answer('What does Base Paint do?',[{id:'x',name:'Base Paint',group:'Special art'}]);assert.equal(unknown.layer_choices.choices[0].kind,'unknown');assert.match(unknown.text,/do not tell me what the layer contains/);
const hidden=L.focusedLayers('Explain Base Paint',[{id:'x',name:'Base Paint',group:'Paintable Area',visible:true,groupChain:[{visible:false}]}]);assert.equal(hidden.choices[0].visible,false);
const bounded=L.answer('Explain Base Paint',Array.from({length:400},(_,i)=>({id:'layer-'+i,name:'Base Paint',group:'Group '+i})));assert.equal(bounded.layer_choices.observed_matches,300);assert.equal(bounded.layer_choices.choices.length,12);assert.equal(bounded.layer_choices.unread_records,100);assert.match(bounded.chat_summary,/bounded/);
const metadata={file:'reference.psd',layer_groups:['Paintable Area','Custom Spec Map / Red Channel Metallic'],layer_labels:['Paintable Area / Base Paint','Custom Spec Map / Red Channel Metallic / Base Paint'],more_labels_omitted:true};
const reference=L.answerReference('What does Base Paint do?',metadata);assert.equal(reference.live_context,false);assert.equal(reference.reference_context,true);assert.ok(reference.layer_choices.choices.every(c=>c.id===null));assert.match(reference.chat_summary,/does not verify your open file/);assert.match(reference.chat_summary,/bounded/);
assert.equal(JSON.stringify(rows),before,'No layer mutation');
const w={console,Set,Map,Date,Promise,document:{readyState:'loading',getElementById:()=>null,addEventListener(){}},localStorage:{getItem:()=>null,setItem(){}},setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},clearInterval(){},addEventListener(){},SpbProCar:{roles:()=>rows}};w.window=w;vm.createContext(w);
for(const file of ['mcp/chatgpt/car-knowledge/layer-reading.js','mcp/chatgpt/design-intent.js','mcp/chatgpt/car-knowledge/core.js','mcp/chatgpt/car-knowledge/offline-answer.js','js/spb-encyclopedia-data.js','js/spb-enc-search.js','mcp/chatgpt/candidates/spb-offline-answer.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),w);
(async()=>{
 await w.SpbOfflineAnswer.load(async name=>{try{return JSON.parse(fs.readFileSync(name==='cars.json'?path.join(__dirname,'build/cars.json'):path.join(root,'data/encyclopedia',name),'utf8'));}catch{return null;}});
 for(const q of ['What does Base Paint do?','Which Base Paint should I use for body colour?']){
  const direct=w.SpbCarReferenceAnswer.readOnlyQuestion(q);assert.equal(direct.answer.id,'assistant.template_layers');assert.equal(direct.answer.layer_choices.observed_matches,4);
  const routed=w.SpbOfflineAnswer.route(q,{layers:rows});assert.equal(routed.cls,'ANSWER');assert.equal(routed.answer.layer_choices.observed_matches,4);assert.equal(routed.answer.actions.length,0);
 }
 const other=w.SpbOfflineAnswer.route('What does Base Paint do in the Ferrari 296 GT3 template?',{layers:rows});assert.notEqual(other.answer&&other.answer.live_context,true,'A named different car cannot receive open ARCA layer choices');
 console.log(JSON.stringify({pass:true,actual_layers:42,exact_live_choices:4,material_copies:3,read_only_offline_routes:4,bounded_reference:'pass',mixed_edit_refusals:6,other_car_isolation:'pass'}));
})().catch(e=>{console.error(e);process.exitCode=1;});
