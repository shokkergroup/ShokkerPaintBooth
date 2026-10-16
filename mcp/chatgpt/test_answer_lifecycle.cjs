'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),pro=fs.readFileSync(path.join(__dirname,'candidates/spb-pro-ai.js'),'utf8');
const w={console,Date,Math,JSON,Promise,Set,Map,setTimeout(){},setInterval(){},document:{readyState:'loading',addEventListener(){},querySelector(){return null},getElementById(){return null}},localStorage:{getItem:k=>k==='SPB_CONVO'?'1':null,setItem(){}}};w.window=w;vm.createContext(w);
for(const file of ['mcp/chatgpt/candidates/spb-convo-state.js','mcp/chatgpt/editor-capabilities.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),w,{filename:file});
let card={},id=0;const input={value:''},entries=[];
Object.assign(w,{zones:[{id:'body-zone',name:'Everything Else',pattern:'checker',scale:.6,patternSpecOpacity:0,sourceLayers:['body']},{id:'empty',name:'Empty'}],selectedZoneIndex:0,_psdLayers:[{id:'body',name:'Body'},{id:'numbers',name:'Numbers'}],PATTERNS:[{id:'checker',name:'Diner Checkerboard'}],SpbConversationScope:{observe(){},stamp:()=>1,current:x=>x===1},SpbAiConnect:{relaying:()=>false},SpbDesignIntent:require('./design-intent.js'),SpbNamedPatternRefinement:require('./named-pattern-refinement.js'),SpbOfflineBuilder:{offlineMode:()=>true,state:()=>card,showAnswer:(r,text)=>{card={answer:r,text};}},SpbPbn:{draw(){}},_busy:false,_log:[],_panel:{setAttribute(){},querySelectorAll:()=>[],querySelector:s=>s==='.spb-pai-input'?input:null}});
// Execute the actual generated terminal conversation call inside the finish stub.
// Native acceptance separately exercises the whole real finish/verification path.
const marker='try { if (window.SpbConvo && SpbConvo.on()) SpbConvo.fromEntry(entry, r, text); } catch (eCV5) {} completeMaterialAnswer(entry,r,text);';assert.ok(pro.includes(marker));
w.finish=(r,text,kind)=>{const entry={id:++id,role:'ai',text:r.text,kind,lines:[],notes:[]};entries.push({entry,result:r});w._log.push(entry);Object.assign(w,{entry,r,text});vm.runInContext(marker,w);return r;};
const begin=pro.indexOf('    var _composerFinishing = 0'),end=pro.indexOf('    function finish(',begin);vm.runInContext(pro.slice(begin,end),w);
vm.runInContext(pro.slice(pro.indexOf('    var _patternAdviceSnapshot = null;'),pro.indexOf('    function offlineNamedZoneMaterial(parsed) {')),w);
const start=pro.indexOf('    function send(text, o) {'),next=pro.slice(start+1).match(/^    function \w+\(/m);vm.runInContext(pro.slice(start,start+1+next.index).replace('// CAR-KNOWLEDGE:',"throw Error('full route'); // CAR-KNOWLEDGE:"),w);
const stateBefore=JSON.stringify({zones:w.zones,layers:w._psdLayers});
// Begin from the native failure: a stale hard answer slot left by empty asked.
w.SpbConvo.noteRoute({cls:'ASK'},'Prior factual question');assert.deepEqual(JSON.parse(JSON.stringify(w.SpbConvo.pending().missing)),[]);
const first='What are my current checker pattern settings? Explain only.';
let r=w.send(first);assert.equal(r.asked,undefined);assert.equal(w._completedReadOnlyAnswers.has(r),true);assert.equal(w._completedReadOnlyAnswers.has(JSON.parse(JSON.stringify(r))),false);assert.equal(entries.at(-1).entry.kind,'noaction');assert.equal(w.SpbConvo.view().history.at(-1).act,'answer');assert.equal(w.SpbConvo.pending(),null);
const actualFeedback=pro.split('\n').find(l=>l.includes('entry.noChange = true;')&&l.includes('_completedReadOnlyAnswers.has(r)'));assert.ok(actualFeedback);
function noChange(payload){w.r=payload;w.entry={lines:[],notes:[]};vm.runInContext(actualFeedback,w);return !!w.entry.noChange;}
assert.equal(noChange(r),false,'Actual local completed answer is not a failed paint edit');assert.equal(noChange({...JSON.parse(JSON.stringify(r)),readOnlyAnswer:true}),true,'Saved/model JSON boolean cannot suppress unchanged-edit feedback');
r=w.send('And what does spec amount 0% mean? Please explain only.');assert.equal(r.asked,undefined);assert.equal(w.SpbConvo.view().history.at(-1).act,'answer');assert.equal(w.SpbConvo.pending(),null);assert.equal(w.SpbConvo.changes().length,0);
w.selectedZoneIndex=1;r=w.send('And what does spec amount 0% mean? Please explain only.');assert.ok(r.asked);assert.equal(w._completedReadOnlyAnswers.has(r),false);assert.match(r.asked.question,/selected zone changed/);assert.equal(entries.at(-1).entry.kind,'ask');assert.equal(w.SpbConvo.view().history.at(-1).act,'ask');assert.deepEqual(JSON.parse(JSON.stringify(w.SpbConvo.pending().missing)),['answer']);
w.selectedZoneIndex=0;r=w.send(first);assert.equal(r.asked,undefined);assert.equal(w.SpbConvo.pending(),null);assert.equal(w.SpbConvo.view().history.at(-1).act,'answer');
// Design proposals remain descriptive answers, not commits or executable offers.
r=w.send('Give me two black and gold directions. Advice only.');assert.equal(r.asked,undefined);assert.equal(r.design_proposals.executable,false);assert.equal(w.SpbConvo.view().history.at(-1).act,'answer');assert.equal(w.SpbConvo.changes().length,0);
assert.equal(JSON.stringify({zones:w.zones,layers:w._psdLayers}),stateBefore);
// The real producer payload deliberately has no enc field. Its topic must be
// attached by local identity, not assumed from a fabricated test/model object.
r=w.send('Can I keep my sponsors matte while the body stays chrome? Please explain only.');
assert.equal(r.enc,undefined);assert.equal(w._completedMaterialFacts.has(r),true);assert.equal(r.documentStamp,1);assert.equal(w.SpbConvo.pending(),null);
assert.equal(w.SpbConvo.view().history.at(-1).look,undefined);assert.equal(w.SpbConvo.view().history.at(-1).targets,undefined);assert.equal(w.SpbConvo.changes().length,0);
// Kill switch retains the original asked call and actual original store behavior.
w.SPB_CX3_OFF=true;w.SpbEditorCapabilities.answer=()=>({cls:'ANSWER',answer:{id:'assistant.live_editor_capabilities',text:'Original factual card'}});
r=w.send('Factual test');assert.ok(r.asked);assert.equal(entries.at(-1).entry.kind,'ask');assert.equal(w.SpbConvo.view().history.at(-1).act,'ask');
console.log(JSON.stringify({pass:true,actual_generated_Send_and_terminal_store_call:true,real_conversation_kernel:true,completed_answers_not_pending_questions:true,genuine_stale_target_asks_preserved:true,new_answer_retires_hard_slot:true,descriptive_proposals_not_commits:true,source_state_unchanged:true,kill_switch:true}));
