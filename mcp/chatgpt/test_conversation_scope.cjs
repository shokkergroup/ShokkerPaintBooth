'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),read=file=>fs.readFileSync(path.join(root,file),'utf8');
let source={path:'C:/isolated/car-a.psd',fingerprint:'hash-a',generation:1},paintReads=0,notesCleared=0,mapsForgotten=0,aborts=0;
const w={console,Promise,Date,Set,Map,Uint8Array,AbortController,
 setTimeout:()=>0,setInterval:()=>0,clearTimeout(){},clearInterval(){},
 localStorage:{getItem:()=>null,setItem(){notesCleared++;}},
 document:{readyState:'loading',addEventListener(){},getElementById:()=>null},
 SPBSourceLoadTransaction:{getCommittedPath:()=>source.path,getCommittedFingerprint:()=>source.fingerprint,getGeneration:()=>source.generation},
 SpbTellNLU:{buildIndex:()=>({})},SpbAI:{cached:()=>({configured:false})},SpbProZone:{SCHEMA:{},zonesForModel(){paintReads++;return [];},paintColours:()=>[]},
 SpbProCar:{forget(){mapsForgotten++;},signature:()=>source.path},zones:[],selectedZoneIndex:-1,MAX_ZONES:40};
w.window=w;vm.createContext(w);
vm.runInContext(read('js/spb-convo-state.js'),w);
const ai=read('mcp/chatgpt/candidates/spb-pro-ai.js').replace('window.spbProAI = {',`window.spbProAI = {
 _testTools:makeTools,_testApply:applyQueue,
 _testOriginalAsk:askForDocument,_testSetAsk:function(fn){askForDocument=fn;},
 _testSeed:function(){HIST.push({role:'user',content:'old'});RECENT.push('old');_log.push({role:'user',text:'Keep blue and sponsors. No glitter.'},{role:'ai',text:'Try understated satin gold.'});
 _orig={snap:'old-snapshot'};_r14={opts:['old-option']};_offlineLast={plan:'old-plan'};_last={editCtx:{target:'old-target'}};_ctl={abort:function(){window._testAborted();}};},
 _testLegacy:function(){return {hist:HIST.length,recent:RECENT.length,orig:!!_orig,r14:!!_r14,offline:!!_offlineLast,last:!!_last};},`);
w._testAborted=()=>aborts++;
vm.runInContext(ai,w);
vm.runInContext(read('mcp/chatgpt/candidates/spb-offline-builder.js'),w);
const oa=read('mcp/chatgpt/candidates/spb-offline-answer.js').replace('W.SpbOfflineAnswer = {',`W.SpbOfflineAnswer = {
 _testSeed:function(){CS={pending:{asked:'old'},topic:'old',list:['old'],t:Date.now()};TRAIL={text:'old'};RUNC={text:'old'};IA1_LW={old:true};W5C_HIST=['old'];},
 _testLegacy:function(){return {pending:!!CS.pending,topic:!!CS.topic,list:!!CS.list,trail:!!TRAIL,run:!!RUNC,waiting:!!IA1_LW,hist:W5C_HIST.length};},`);
vm.runInContext(oa,w);
vm.runInContext(read('mcp/chatgpt/candidates/spb-pbn.js').replace('W.SpbPbn = {', `W.SpbPbn = {
 _testSeed:function(){S.text='old';S.picks=[{slot:'target',val:'old'}];RDM={old:{steps:['old']}};RDN=1;CUR={opts:['old']};},
 _testLegacy:function(){return {text:S.text,picks:S.picks.length,cache:Object.keys(RDM).length,question:!!CUR};},`),w);
vm.runInContext(read('mcp/chatgpt/conversation-scope.js'),w);
vm.runInContext(read('mcp/chatgpt/design-brief.js'),w);
const C=w.SpbConvo,S=w.SpbConversationScope,B=w.SpbDesignBrief,A=w.spbProAI,O=w.SpbOfflineAnswer;
const canvas=read('mcp/chatgpt/candidates/paint-booth-3-canvas.js');
const begin=canvas.indexOf('        function _spbSourceLoadResult('),end=canvas.indexOf('        async function _spbFingerprintBytes(',begin);
assert.ok(begin>=0&&end>begin);vm.runInContext(canvas.slice(begin,end),w);
function result(ok){w._spbSourceLoadGeneration=source.generation;w._spbCommittedSourcePath=source.path;w._spbCommittedSourceFingerprint=source.fingerprint;w._psdPath='';return w._spbSourceLoadResult(null,ok,{});}
function seed(){
 A._testSeed();O._testSeed();w.SpbPbn._testSeed();const b=w.SpbOfflineBuilder.state();b.steps=[{target:'old-target'}];b.ran={at:1};b.s5frame={old:true};
 C.turn('Make the hood blue');C.commit({targets:[{kind:'part',part:'hood'}],zone_ids:['a-zone'],undo_id:'a-undo'});
 C.offer({kind:'options',items:['Pearl blue','Satin gold'],for:[{kind:'part',part:'hood'}]});
}
seed();const saved=B.captureSession(),stamp=S.stamp(),queue=[];
const oldTools=A._testTools(queue,null,{online:true}),oldRead=oldTools.find(t=>t.name==='get_state');
assert.ok(oldRead);assert.equal(queue._documentStamp,stamp);
source.generation++;result(false);
assert.equal(S.current(stamp),true,'Failed loads leave current conversation usable');assert.ok(C.lastOffer());assert.equal(A.log().length,2);
source={path:'C:/isolated/car-b.psd',fingerprint:'hash-b',generation:3};result(true);
assert.equal(C.view().last_offer,null);assert.equal(C.view().last_change,null);assert.equal(C.view().pending,null);
assert.equal(A.log().length,0);assert.deepEqual(JSON.parse(JSON.stringify(A._testLegacy())),{hist:0,recent:0,orig:false,r14:false,offline:false,last:false});
assert.deepEqual(JSON.parse(JSON.stringify(O._testLegacy())),{pending:false,topic:false,list:false,trail:false,run:false,waiting:false,hist:0});
assert.equal(w.SpbOfflineBuilder.state().steps.length,0);assert.equal(w.SpbOfflineBuilder.state().ran,null);assert.equal(w.SpbOfflineBuilder.state().s5frame,undefined);
assert.deepEqual(JSON.parse(JSON.stringify(w.SpbPbn._testLegacy())),{text:'',picks:0,cache:0,question:false});
assert.equal(A._undoLast(),false);assert.equal(A.restoreVersion('orig'),false);assert.equal(aborts,1);assert.equal(notesCleared,0);assert.equal(mapsForgotten,0);
const readCount=paintReads;assert.match(oldRead.handler({}).error,/paint changed/);assert.equal(paintReads,readCount);
const rejected=A._testApply(queue,'old paint');assert.equal(rejected.results.length,0);assert.match(rejected.failed[0],/paint changed/i);assert.equal(w.zones.length,0);
assert.equal(B.capture('b'),null);
source={path:'C:/isolated/car-a.psd',fingerprint:'hash-a',generation:4};result(true);B.restoreSession(saved);
assert.match(B.view().turns[0].text,/Keep blue/);assert.match(B.view().turns[1].text,/satin gold/);
assert.equal(C.lastOffer(),null);assert.equal(A._undoLast(),false,'A successful rollback restores quotes, not executable references');
seed();const sameStamp=S.stamp();source.generation++;result(true);assert.equal(S.current(sameStamp),false);assert.equal(C.lastOffer(),null);
// A direct committed-path change without the result hook is caught before the next read.
seed();source={path:'C:/isolated/car-c.psd',fingerprint:'hash-c',generation:6};A.state();assert.equal(A.log().length,0);assert.equal(C.lastOffer(),null);
console.log('PASS actual source boundary clears offers, targets, Undo, versions, legacy chat, Offline follow-ups and builder choices; failed loads preserve state; rollback restores discussion only; no notes/maps cleared or paint mutated');
(async()=>{
 let release;
 A._testSetAsk(()=>new Promise(resolve=>{release=resolve;}));
 const pending=A.ask('Use satin gold on the hood');
 source={path:'C:/isolated/car-d.psd',fingerprint:'hash-d',generation:7};result(true);
 release({text:'Old answer',queue:[{kind:'add',spec:{color:'#ffd700'}}]});
 const stale=await pending;assert.match(stale.error.message,/paint changed/i);assert.equal(stale.queue.length,0);
 await A.finish(stale,'Use satin gold on the hood','ask');assert.equal(A.log().filter(r=>r.role==='ai').length,0);assert.equal(w.zones.length,0);
 // Exercise the actual ask -> warm -> runTurn2 -> model-tools -> completion path.
 A._testSetAsk(A._testOriginalAsk);w.SpbAI.cached=()=>({configured:true});
 let modelTools,finishModel;
 w.SpbAI.run=opts=>{modelTools=opts.tools;return new Promise(resolve=>{finishModel=resolve;});};
 const actualPending=A.ask('Discuss black and gold; do not apply anything',{forceAI:true,noPreflight:true,noReview:true});
 for(let i=0;i<30&&!finishModel;i++)await Promise.resolve();
 assert.ok(finishModel,'The actual model path reached its bounded test transport');
 source={path:'C:/isolated/car-d2.psd',fingerprint:'hash-d2',generation:8};result(true);
 assert.match(modelTools.find(t=>t.name==='get_state').handler({}).error,/paint changed/);
 finishModel({text:'A late model proposal',usage:{cost:0},calls:1,tools:[]});
 const actualStale=await actualPending;assert.match(actualStale.error.message,/paint changed/i);assert.equal(actualStale.queue.length,0);
 assert.equal(A._testLegacy().hist,0,'A late model result must not repopulate another document history');
 const freshTools=A._testTools([],null,{online:true}),fresh=freshTools.find(t=>t.name==='get_state');assert.ok(fresh.handler({}).zones);
 // Reset failure is visible and blocks a previously obtained tool.
 const reset=A._sourceChanged;A._sourceChanged=()=>{throw Error('simulated reset error');};
 source={path:'C:/isolated/car-e.psd',fingerprint:'hash-e',generation:9};result(true);
 assert.equal(S.status().available,false);assert.equal(S.status().failed_resets[0],'Full Editor conversation');assert.match(fresh.handler({}).error,/paint changed/i);
 A._sourceChanged=reset;
 console.log('PASS old tool closures/queues and delayed ask results reject after a source switch; fresh reads work; reset failure blocks execution');
})().catch(e=>{console.error(e);process.exitCode=1;});
