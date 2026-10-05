'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const candidate='_easy_claude_work/ai14h_w86_review/candidate/spb-pro-ai.js',base='_easy_claude_work/ai14h_w86_review/candidate/spb-pro-ai.base.js';
const editPath='_easy_claude_work/ai14h_generation3_runtime4/js/spb-pro-edit.js',designPath='_easy_claude_work/ai14h_generation3_runtime4/js/spb-pro-design.js',opPath='js/spb-ai-operation.js';
function sha(f){return crypto.createHash('sha256').update(fs.readFileSync(path.join(root,f))).digest('hex');}
for(const [p,h] of [[base,'e28770330994ffc04364d0a48e88b98b69d25f9848e23d56cc1cea07165da713'],[opPath,'47587a1a53a35ce7e58825bac864bd75c2421d26c19791957f57bb199a7000c6'],[editPath,'99703873013e198857d9aceaa334821098e53dcaa9d55e14dbd1ec50e58604de'],[designPath,'0533393ff5f2170236f60d4ed489c7ae52f98805e12b0764da67a967f756f2e8']])assert.equal(sha(p),h,`pinned input changed: ${p}`);
const controller=fs.readFileSync(path.join(root,candidate),'utf8');
function sliceBetween(src,start,end,label){const a=src.indexOf(start),b=src.indexOf(end,a);assert(a>=0&&b>a,`actual ${label} bounds`);return src.slice(a,b);}
const offlineAskSrc=sliceBetween(controller,'    function offlineAsk(text, o) {','    function offlineAskCore(text, o)', 'offlineAsk');
const editEnvSrc=sliceBetween(controller,'    function editEnv() {','    // COPILOT-FIX 2026-10-04 (owner:', 'editEnv');
const editPlanSrc=sliceBetween(controller,'    function editPlan(text) {','    function editReply(', 'editPlan');
const askSource=fs.readFileSync(path.join(root,base),'utf8');
const askSrc=sliceBetween(askSource,'    function ask(text,o) {','    function askForTicket(', 'baseline ask');
const editSource=fs.readFileSync(path.join(root,editPath),'utf8'),designSource=fs.readFileSync(path.join(root,designPath),'utf8');
const cases=[
 {id:'W86-01 warm/current rebind then fresh edit plan',change:null,expected:'compiled'},
 {id:'W86-02 cancel during delayed CAR warm',change:'cancel',expected:'cancelled'},
 {id:'W86-03 same-path/new-generation source switch during warm',change:'source',expected:'cancelled'},
 {id:'W86-04 manual zone revision during warm',change:'revision',expected:'cancelled'},
 {id:'W86-05 CAR warm rejection stays truthful and queues nothing',change:'reject',expected:'refusal'}
];
async function run(c){
 const w={console,Promise,setTimeout,clearTimeout,zones:[{id:'roof1',name:'Saved green roof',base:'gloss',baseColorMode:'solid',baseColor:'#1f8a3b',strength:1,_spbAIPartMemoryPending:{schema:'test-pending',provenance:{r:'{"island":"roof"}'}}}]};w.window=w;vm.createContext(w);vm.runInContext('var _partMemoryWarmAttemptTicket=null;var _envMemo=null;',w);
 vm.runInContext(designSource,w,{filename:designPath});vm.runInContext(editSource,w,{filename:editPath});
 let doc={sourceGeneration:2,path:'C:/car.psd',fingerprint:'file-sha256:'+'a'.repeat(64),width:2048,height:2048},revision='zone-before';
 const manager=require(path.join(root,opPath)).create(()=>Object.assign({},doc),()=>revision);
 let resolveWarm,rejectWarm,hydrations=0,compiles=0,proofCalls=0;const events=[];const currentZoneColour=[{zone_id:'roof1',zone:'Saved green roof',hex:'#1f8a3b',share_pct:7,layers:[]}];
 const warmP=new Promise((r,j)=>{resolveWarm=r;rejectWarm=j;});
 Object.assign(w,{D:w.SpbProDesign,E:w.SpbProEdit,CAR:{paintableMask:()=>null},Z:{paintColours:()=>[{hex:'#01ff00',share_pct:28,name:'neon green'}]},
   zoneColours:()=>{events.push('env-build');return w.zones[0]._aiPartProv?currentZoneColour:[]},shownShares:p=>p,layersInfo:()=>[],lastEditCtx:()=>null,numbersInfo:()=>[],
   _envMemo:null,_elemCache:null,_busy:false,_advLast:null,_offlineLast:null,_reqText:'',_specOnlyReq:false,_beforeImg:null,_skipParts:false,_absent:{},NUM_FIX_RE:/z/,NOT_ELEM_RE:/z/,layerVisRequest:()=>null,offlineCannot:()=>null,
   operationManager:()=>manager,operationStart:()=>manager.start(),operationCurrent:t=>manager.current(t),operationRelease:t=>{if(manager.owns(t))w._busy=false;},operationPublish:(t,fn)=>{const r=manager.publish(t,fn);return r&&!r.refused?r.value:null;},operationCanceled:()=>({cancelled:true,stale:true,queue:[]}),
   warm:()=>{events.push('warm-start');return c.change==='reject'?Promise.reject(new Error('warm fail')):warmP;},
   hydratePartMemory:()=>{if(w.zones[0]._spbAIPartMemoryPending){assert(manager.current(manager.owner()),'rehydration only under current ticket');w.zones[0]._aiPartProv={r:'{"island":"roof"}'};w.zones[0]._aiPartSource={path:doc.path,fingerprint:doc.fingerprint,generation:doc.sourceGeneration,width:2048,height:2048};delete w.zones[0]._spbAIPartMemoryPending;hydrations++;events.push('rebind');}},
   elementRunCurrent:()=>true,elementPaintChangedResult:()=>({cancelled:true}),offlineInstructionPreflight:()=>null,
   offlineMaterialPlan:()=>null,advisorOwns:()=>false,offlineMaterialAsk:()=>({queue:[]}),offlineCoveredPartAsk:()=>({queue:[]}),
   START_OVER_RE:/^\s*start over\s*$/i,_offlineLast:null,editYieldsToStack:()=>false,advisorIntent:()=>null,offlineAskCore:()=>({route:'core',queue:[]}),
   currentPartZoneOwners:(parts,hits)=>{proofCalls++;return [{zone_id:'roof1',part:'roof'}];},
   offlineEditAsk:(text,ed)=>{compiles++;events.push('compile');const env=w.__editEnv();const plan=w.SpbProEdit.plan(text,env);const compiled=w.SpbProEdit.compile(plan,env);return {route:'edit',queue:compiled.zones,compiled};},
   editReply:text=>({route:'refusal',text,queue:[]}),editInstructionPreflight:null,render:()=>{},captureOriginal:()=>{},intentSpecOnly:()=>false
 });
 // Use the actual editEnv/editPlan functions, with only their app-state readers stubbed above.
 vm.runInContext(editEnvSrc+'\nthis.__editEnv=editEnv;',w,{filename:'actual-editEnv'});vm.runInContext(editPlanSrc+'\nthis.__editPlan=editPlan;',w,{filename:'actual-editPlan'});w.editPlan=w.__editPlan;
 vm.runInContext(offlineAskSrc+'\nthis.__offlineAsk=offlineAsk;',w,{filename:'actual-offlineAsk'});
 const ticket=manager.start();const o={_spbOperation:ticket};
 const resultP=w.__offlineAsk('Make green on the roof blue',o);assert(resultP&&typeof resultP.then==='function');await Promise.resolve();
 if(c.change==='cancel')manager.cancel(ticket);
 if(c.change==='source')doc={...doc,sourceGeneration:3};
 if(c.change==='revision')revision='manual-edit';
 if(c.expected!=='refusal')resolveWarm();
 const result=await resultP;
 if(c.expected==='compiled'){
   assert.equal(hydrations,1);assert.equal(compiles,1);assert.equal(result.route,'edit');
   assert.deepEqual(events,['warm-start','rebind','env-build','compile']);
   assert.equal(result.compiled.zones[0].region.part,'roof');
   assert.deepEqual(Array.from(result.compiled.zones[0].region.colors),['#01ff00'],'W89 classifier ambiguity intentionally preserved for separate repair');
   assert.equal(proofCalls,0,'E compile r.entries gate currently bypasses the verified owner callback; W89 scope remains');
 }else if(c.expected==='cancelled'){
   assert.equal(result.cancelled,true);assert.equal(hydrations,0);assert.equal(compiles,0);assert.deepEqual(events,['warm-start']);
 }else {assert.equal(result.route,'refusal');assert.match(result.text,/Nothing was changed/);assert.equal(hydrations,0);assert.equal(compiles,0);assert.deepEqual(events,['warm-start']);}
 return {id:c.id,pass:true,expected:c.expected,hydrations,compiles,proofCalls,result:result.route||'cancelled',events};
}
(async()=>{const rows=[];for(const c of cases)rows.push(await run(c));for(const mode of ['external-lease','busy']){const w={Promise};w.window=w;vm.createContext(w);const manager=require(path.join(root,opPath)).create(()=>({sourceGeneration:1}),()=>1);let routeCalls=0;Object.assign(w,{_busy:mode==='busy',operationStart:()=>manager.start(),operationCurrent:t=>manager.current(t),operationRelease:t=>{if(manager.owns(t))w._busy=false;},operationCanceled:()=>({cancelled:true}),operationBind:(v,t)=>manager.bind(v,t),operationManager:()=>manager,offlineInstructionPreflight:()=>null,askForTicket:()=>{routeCalls++;return Promise.resolve({offline:true,queue:[]});},window:w,SpbAiLease:{internal:()=>mode!=='external-lease'}});vm.runInContext(askSrc+'\nthis.__ask=ask;',w,{filename:'actual-ask-guards'});const value=await w.__ask('Make green on the roof blue');assert.equal(routeCalls,0);assert(value.error);rows.push({id:'W86-ASK-'+mode,pass:true,expected:'guard before ticketed route',askCalls:routeCalls,error:value.error.message});}const w={Promise};w.window=w;vm.createContext(w);const manager=require(path.join(root,opPath)).create(()=>({sourceGeneration:1}),()=>1);let routeCalls=0;Object.assign(w,{_busy:false,operationStart:()=>manager.start(),operationCurrent:t=>manager.current(t),operationRelease:t=>{if(manager.owns(t))w._busy=false;},operationCanceled:()=>({cancelled:true}),operationBind:(v,t)=>manager.bind(v,t),operationManager:()=>manager,offlineInstructionPreflight:()=>null,askForTicket:(text,o)=>{routeCalls++;assert(manager.current(o._spbOperation));return Promise.resolve({offline:true,queue:[]});},window:w,SpbAiLease:{internal:()=>true}});vm.runInContext(askSrc+'\nthis.__ask=ask;',w,{filename:'actual-ask-normal'});const normal=await w.__ask('What does my paint do?');assert.equal(routeCalls,1);assert.equal(normal.queue.length,0);rows.push({id:'W86-ASK-normal',pass:true,expected:'current ticket reaches ticketed ask',askCalls:routeCalls});const report={status:'PASS_WITH_LIMITS',task:'W86 private offlineAsk warm-before-rehydrate candidate',source:{baseline:{path:base,sha256:sha(base)},candidate:{path:candidate,sha256:sha(candidate)},operation:{path:opPath,sha256:sha(opPath)},edit:{path:editPath,sha256:sha(editPath)},design:{path:designPath,sha256:sha(designPath)}},counts:{cases:rows.length,passed:rows.length,failed:0,providerCalls:0,nativeCalls:0},rows,limits:['Actual candidate offlineAsk, editEnv, editPlan and E.plan/E.compile run in a VM; app readers, CAR.ensure, successful rebind, and offlineEditAsk application wrapper are controlled fakes.','Actual SpbAiOperation ticket/current/revision logic is used. Delay races cover cancel, committed source-generation replacement, and manual zone revision before hydration.','Current E.compile source-identity fallback remains a known W89 gap: its result still selects source #01ff00 and bypasses currentPartZoneOwners when a source-color entry exists. This candidate does not claim the W86 owner edit is fixed end-to-end.','No native, provider, or server calls; isolated candidate only.']};fs.writeFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_W86_WARM_REBIND_CANDIDATE_2026-10-04.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));})().catch(e=>{console.error(e);process.exitCode=1;});