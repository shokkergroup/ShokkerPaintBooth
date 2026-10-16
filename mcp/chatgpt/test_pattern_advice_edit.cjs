'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),P=require('./named-pattern-refinement.js');
const z={id:'target',name:'Everything Else',pattern:'checker',scale:0.6,sourceLayers:['body']};
const a={editor_topic:'pattern',pattern_zone_id:z.id,pattern_id:'checker',document_stamp:'doc'};
const snap={answer:a,target:z},env={zones:[z],selected:0,snapshot:snap,current:true,unchanged:true};
for(const q of ['Make it a little finer.','Please make that pattern coarser.','Could you please make it slightly smaller?','Make this pattern larger']){const p=P.advice(q,a,env);assert.equal(p.kind,'edit');assert.equal(p.selected,true);assert.equal(p.adviceSnapshot,snap);}
for(const q of ['Would coarser help?','How can I make it finer?','Make it finer then hide Numbers','Make it finer and recolour Body blue','Make it finer; export','Finer?','Make it a little finer but leave sponsors alone'])assert.equal(P.advice(q,a,env),null,q);
assert.equal(P.advice('Make it finer',{editor_topic:'doctor'},env),null);
for(const e of [{...env,current:false},{...env,unchanged:false},{...env,snapshot:null},{...env,selected:-1},{...env,zones:[{...z}]},{...env,zones:[{...z,pattern:'hound'}]}])assert.equal(P.advice('Make it finer',a,e).kind,'clarify');
assert.equal(P.advice('Make it finer',{...a},env).kind,'clarify','Restored JSON card is not the fresh locally observed card');
assert.equal(P.advice('Make it finer',{...a,needs_pattern_target:true},env).kind,'clarify');
const source=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8');
let epoch='doc',topic={},settled=[],compiled=[],warmResolve,delayWarm=false;
const input={value:''},w={console,Promise,Math,zones:[z],selectedZoneIndex:0,_psdLayers:[{id:'body',name:'Body'}],PATTERNS:[{id:'checker',name:'Checker'}],_log:[],_busy:false,_panel:{setAttribute(){},querySelectorAll:()=>[],querySelector:s=>s==='.spb-pai-input'?input:null},SpbNamedPatternRefinement:P,SpbDesignIntent:require('./design-intent.js'),SpbConversationScope:{observe(){},stamp:()=>epoch,current:s=>s===epoch,status:()=>({available:true})},SpbAiConnect:{relaying:()=>false},SpbOfflineBuilder:{offlineMode:()=>true,state:()=>topic,showAnswer:(r,text)=>{topic={answer:r,text};},showSteps:()=>{}},SpbPbn:{draw(){}},AI:{cached:()=>({})},captureOriginal(){},w19StaleBegin(){},editReply:text=>({text,queue:[]}),finish:(r,text)=>{settled.push(r);w._log.push({role:'ai',text:r.text});return Promise.resolve(r);},warm:()=>delayWarm?new Promise(resolve=>{warmResolve=resolve;}):Promise.resolve()};
w.window=w;vm.createContext(w);
w.render=()=>{};
vm.runInContext(fs.readFileSync(path.join(__dirname,'editor-capabilities.js'),'utf8'),w);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../../js/spb-intent-plan.js'),'utf8'),w);
w.undoSigNow=()=>({zones:w.zones.map(v=>({sig:JSON.stringify(v)})),layers:JSON.parse(JSON.stringify(w._psdLayers))});
w.undoSameZones=(a,b)=>JSON.stringify(a.zones)===JSON.stringify(b.zones);w.undoSameLayers=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
w.s5RunReply=(text,unused,frame)=>{const plan=w.SpbIntentPlan.plan(frame,{zones:w.zones.map(v=>({id:v.id,name:v.name,pattern:P.patternId(v),patternScale:v.scale})),layers:[]});assert.equal(plan.ok,true);compiled.push(plan);return {text:'prepared',queue:{_s5plan:plan}};};
vm.runInContext(source.slice(source.indexOf('    var _patternAdviceSnapshot = null;'),source.indexOf('    function offlineNamedZoneMaterial(parsed) {')),w);
vm.runInContext(source.slice(source.indexOf('    var _composerFinishing = 0'),source.indexOf('    function finish(',source.indexOf('    var _composerFinishing = 0'))),w);
const start=source.indexOf('    function send(text, o) {'),cut=source.indexOf('        _visHiddenOk = false;',start);
vm.runInContext(source.slice(start,cut)+'\nthrow Error("legacy route");}',w);
async function flush(){for(let i=0;i<8;i++)await Promise.resolve();}
(async()=>{
 await w.send('What are my current pattern settings?');assert.equal(topic.answer.answer.pattern_id,'checker');
 w.send('Make it a little finer.');await flush();assert.equal(compiled.length,1);const op=compiled[0].steps[0].ops[0];assert.equal(op.zone,z.id);assert.equal(op.spec.pattern.scale,0.465);assert.equal(settled.at(-1).namedPattern.target,z);assert.equal(w.zones.length,1);assert.equal(z.scale,0.6,'Compilation itself does not mutate');
 assert.equal(topic._handledPattern.text,'Make it a little finer.','Completed exact request retains its ownership marker instead of reoffering targets');
 await w.send('What are my current pattern settings?');z.sourceLayers=['other'];w.send('Make it a little finer.');await flush();assert.equal(compiled.length,1);assert.match(settled.at(-1).text,/changed/);z.sourceLayers=['body'];
 await w.send('What are my current pattern settings?');w.selectedZoneIndex=-1;w.send('Make it finer');await flush();assert.equal(compiled.length,1);assert.match(settled.at(-1).text,/selected pattern zone changed/);w.selectedZoneIndex=0;
 await w.send('What are my current pattern settings?');epoch='other';w.send('Make it finer');await flush();assert.equal(compiled.length,1);assert.match(settled.at(-1).text,/project or paint changed/);epoch='doc';
 await w.send('What are my current pattern settings?');delayWarm=true;w.send('Make it finer');z.scale=0.7;warmResolve();await flush();assert.equal(compiled.length,1);assert.match(settled.at(-1).text,/changed while I was checking/);delayWarm=false;z.scale=0.6;
 await w.send('What are my current pattern settings?');w._log.push({role:'user',text:'Which colour goes with blue?'},{role:'ai',text:'Gold'});assert.throws(()=>w.send('Make it finer'),/legacy route/);assert.equal(compiled.length,1,'Unrelated conversation cannot reuse an old factual card');
 await w.send('What are my current pattern settings?');w.SPB_CX3_OFF=true;assert.throws(()=>w.send('Make it finer'),/legacy route/);assert.equal(compiled.length,1);
 console.log(JSON.stringify({pass:true,generated_send_and_advice_snapshot:true,actual_shared_compiler:true,exact_target:true,no_mutation_during_advice_or_compile:true,manual_document_selection_warmup_and_restored_card_guards:true,questions_and_mixed_requests_not_edits:true}));
})().catch(e=>{console.error(e);process.exitCode=1;});
