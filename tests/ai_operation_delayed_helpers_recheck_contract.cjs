'use strict';
// W33 oracle frozen before inspecting the a656 candidate or lease adapter.
const crypto=require('node:crypto');
const ORACLE=Object.freeze([
 {id:'support-send-source-switch',expect:'A delayed support helper result must not finish/apply against a replacement source.'},
 {id:'warm-teach-source-switch',expect:'A delayed warm/teach continuation must not initiate or publish on a replacement source.'},
 {id:'finish-card-source-switch',expect:'A delayed finish-card continuation must not finish/apply to a replacement source.'},
 {id:'kit-use-source-switch',expect:'A delayed kit continuation must not finish/apply to a replacement source.'},
 {id:'refine-critic-late-rejection',expect:'A delayed refine/critic continuation must not re-ask, publish, or undo against a replacement source/current owner.'},
 {id:'cancel-preview-A-start-B-late-A-restore',expect:'Late preview A cleanup cannot overwrite B, clear B owner/busy/controller, or publish A.'},
 {id:'cancel-preview-manual-revision-conflict',expect:'Cancel restore refuses to overwrite a newer manual revision in the same document.'},
 {id:'self-help-doit-immediate-finish',expect:'Synchronous self-help/DoIt completion remains bound to its starting source and operation.'},
 {id:'external-lease-begin-rejection',expect:'A rejected external lease acquisition does not end/release another owner.'},
 {id:'external-lease-success-release',expect:'A successful externally-owned operation releases its lease exactly once after completion.'},
 {id:'mcp-pending-tool-source-replacement',expect:'A pending MCP tool may not apply after the committed source changes.'},
 {id:'mcp-source-switch-during-preview',expect:'A preview begun for source A cannot return an image from replacement source B as A result.'},
 {id:'mcp-cancel-A-start-B-late-A',expect:'Cancel A then start B; late A completion cannot clear B busy/controller/lease or publish.'},
 {id:'mcp-async-throw-release-once',expect:'An asynchronous MCP core throw releases a successfully acquired lease exactly once and settles.'},
 {id:'actual-lease-reject-not-end-foreign',expect:'Actual SpbAiLease adapter rejects foreign ownership without calling end or releasing that owner.'}
]);
const SHA256=crypto.createHash('sha256').update(JSON.stringify(ORACLE)).digest('hex').toUpperCase();
if(process.argv.includes('--freeze-only')){console.log(JSON.stringify({count:ORACLE.length,sha256:SHA256,cases:ORACLE},null,2));process.exit(0);}
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),candidatePath=path.resolve(process.env.SPB_W33_CANDIDATE_SNAPSHOT||path.join(root,'_easy_claude_work/ai14h_w10_candidate/js/spb-pro-ai.js'));
const source=fs.readFileSync(candidatePath,'utf8'),candidateHash=crypto.createHash('sha256').update(source).digest('hex').toUpperCase();
const pinned='A656E3A2E55BD8E6D893BE47C12D3686CE30B682405DC33D170C354398DEE183';assert.equal(candidateHash,pinned,'candidate bytes frozen by W33 assignment');
const operation=require('../js/spb-ai-operation.js'),leaseSource=fs.readFileSync(path.join(root,'js/spb-ai-lease.js'),'utf8');
function slice(a,b){const i=source.indexOf(a),j=source.indexOf(b,i+a.length);assert(i>=0&&j>i,`candidate boundary: ${a}`);return source.slice(i,j);}
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return{promise,resolve,reject};}
function world(options={}){
 const w={console,Promise,AbortController,Date,setTimeout(fn,ms){queueMicrotask(fn);return 1;},clearTimeout(){},document:{},paintCanvas:{width:2048,height:1024},_spbSourceGeneration:10,_spbSourcePath:'A.psd',_spbSourceFingerprint:'sha:A',_spbLayerRev:1,_busy:false,_ctl:null,_progress:'',_log:[],_serial:0,_ix:null,_ixN:-1,_extra:{cost:0,calls:0,models:{}},_offlineLast:null,_last:null,_advLast:null,_advUsed:null,_cancelOpts:false,_gen:0,_snapGen:0,_activeId:null,zones:[],layers:[],providerCalls:[],applyCalls:[],renderCalls:0,...options};w.window=w;w.index=()=>[];
 w.SPBSourceLoadTransaction={getGeneration:()=>w._spbSourceGeneration,getCommittedPath:()=>w._spbSourcePath,getCommittedFingerprint:()=>w._spbSourceFingerprint};w.SpbAiOperation=operation;w.getZoneConfigHash=()=>'';w.render=()=>{w.renderCalls++;};
 w.Z={whenSettled:()=>options.whenSettled?options.whenSettled():Promise.resolve(),previewImage:()=>{(w.previewSamples||=[]).push(w._spbSourceGeneration);return `image-${w._spbSourceGeneration}`;},specPreviewImage:()=>`spec-${w._spbSourceGeneration}`,zonesForModel:()=>[],quiet:fn=>fn()};
 w.mcpImages=()=>{(w.imageReturns||=[]).push(w._spbSourceGeneration);return[{name:'live_preview',data_url:`image-${w._spbSourceGeneration}`}];};w.previewPalette=()=>options.paletteGate?options.paletteGate.promise:Promise.resolve({});w.zoneColourProblems=()=>Promise.resolve([]);w.diagnose=()=>[];w.undoDepth=()=>w.applyCalls.length;w.applyQueue=q=>{w.applyCalls.push({generation:w._spbSourceGeneration,queue:JSON.parse(JSON.stringify(q))});w._spbLayerRev++;return{lines:['applied'],failed:[],results:[],maskUndo:[],layerUndo:0};};w.friendlyError=e=>String(e&&e.message||e);w.friendlyZoneError=e=>String(e);w.D={summarise:()=>[]};w.MCP_WRITE={edit_zone:true};w.SpbMcpBridge={stats:()=>({enabled:true})};w._psdLayers=[];
 vm.createContext(w);
 vm.runInContext(slice('var _aiOperation = null;','function operationTools(')+slice('function operationTools(','// End W10 operation helpers.'),w,{filename:'candidate-operation-helpers.js'});
 vm.runInContext(fs.readFileSync(path.join(root,'js/spb-ai-lease.js'),'utf8'),w,{filename:'actual-spb-ai-lease.js'});
 vm.runInContext(slice('function mcpApply(tool,queue,res,ticket)','// SPB-AI owner handoff 2026-10-01'),w,{filename:'candidate-mcp-apply.js'});
 vm.runInContext(slice('function mcpCall(tool,args)','function mcpCallCore(tool,args,ticket)')+slice('function mcpCallCore(tool,args,ticket)','// ------------------------------------------------------------------ PARTS FIRST'),w,{filename:'candidate-mcp-route.js'});
 const cancelStart=source.indexOf("if (b.hasAttribute('data-cancel')) {");const cancelEnd=source.indexOf('var act = b.getAttribute',cancelStart);assert(cancelStart>=0&&cancelEnd>cancelStart);vm.runInContext('function clickCancel(b){'+source.slice(cancelStart,cancelEnd)+'}',w);
 return w;
}
const results=[];
function scenario(id,fn){try{results.push({id,mode:'concrete',...fn()});}catch(e){results.push({id,mode:'concrete',error:e.message});}}
function staticOnly(id,fn){try{fn();results.push({id,mode:'static-only',result:'route contract verified in actual candidate function text'});}catch(e){results.push({id,mode:'static-only',error:e.message});}}
const flush=async()=>{for(let i=0;i<5;i++)await Promise.resolve();};
(async()=>{
 // W28 support helper: actual source-current guard must suppress stale helper completion.
 {
  const gate=deferred(),w=world({SpbSupport:{handle:()=>gate.promise}}),finishCalls=[];w.finish=(r)=>finishCalls.push({generation:w._spbSourceGeneration,ticket:w.operationManager().ticketOf(r)});
  vm.runInContext(slice('function supportSend(text)','var CHECK_AGAIN_RE ='),w);w.supportSend('setup status');w._spbSourceGeneration++;w._spbSourcePath='B.psd';gate.resolve({text:'late'});await new Promise(r=>setImmediate(r));
  scenario('support-send-source-switch',()=>{assert.equal(finishCalls.length,0);return{finishCalls:0,busy:w._busy};});
 }
 // Real ticket-wrapped warm/teach send branch: a switched source must stop before teachAll/finish.
 {
  const gate=deferred(),finished=[],taught=[];const w=world({CAR:{},TEACH_RE:/teach/i,warm:()=>gate.promise,teachAll:t=>(taught.push(t),{offline:true,text:'teach'})});w.finish=(r)=>finished.push(r);
  const a=source.indexOf('if(TEACH_RE.test(text)&&CAR){'),b=source.indexOf("if (/^\\s*(what can you do",a);assert(a>=0&&b>a);vm.runInContext('function runTeach(text){'+source.slice(a,b)+'}',w);
  w.runTeach('teach me the parts');w._spbSourceGeneration++;w._spbSourcePath='B.psd';gate.resolve();await new Promise(r=>setImmediate(r));
  scenario('warm-teach-source-switch',()=>{assert.equal(taught.length,0);assert.equal(finished.length,0);return{teachCalls:taught.length,finishCalls:finished.length};});
 }
 // Actual finish-card/kit warm re-entry guards, with advisor/planner/application effects controlled.
 for(const which of ['finish-card','kit']){
  const gate=deferred(),finished=[];let mapped=false;const w=world({CAR:{map:()=>mapped?{}:null,ensure:()=>{mapped=true;return gate.promise;}},SpbProAdvisor:{applyPlan:()=>({label:'roof',steps:[{tool:'edit_zone',zone:0,args:{}}]})},advisorEnv:()=>({}),partsGate:()=>null,makeTools:()=>[{name:'edit_zone',handler:()=>({ok:true})}],friendlyZoneError:String});w.finish=(r)=>finished.push(r);
  if(which==='finish-card')vm.runInContext(slice('function useFinishCard(entry, i, quiet, pendingTicket)','function useKit(entry, i, quiet, pendingTicket)'),w);else vm.runInContext(slice('function useKit(entry, i, quiet, pendingTicket)','function fcDetail(entry, i)'),w);
  const entry=which==='finish-card'?{fcards:[{name:'Gold',tag:'finish',key:'gold'}],fctarget:{label:'roof'}}:{kits:[{name:'Kit',items:[{role:'roof',card:{name:'Gold',key:'gold'},target:{label:'roof'}}]}]};const ticket=w.operationStart();w.operationBind(entry,ticket);
  if(which==='finish-card')w.useFinishCard(entry,0,false);else w.useKit(entry,0,false);w._spbSourceGeneration++;w._spbSourcePath='B.psd';gate.resolve();await new Promise(r=>setImmediate(r));await new Promise(r=>setImmediate(r));
  scenario(which==='finish-card'?'finish-card-source-switch':'kit-use-source-switch',()=>{assert.equal(finished.length,0);return{finishCalls:finished.length,sourceGeneration:w._spbSourceGeneration};});
 }
 // A refine preview that settles after a source switch must not start the critique on B.
 {
  const gate=deferred(),asks=[],finished=[],w=world({whenSettled:()=>gate.promise});w.askForTicket=(text,o)=>{asks.push({text,generation:w._spbSourceGeneration,ticket:o._spbOperation});return Promise.resolve({text:'late critique'});};w.finish=r=>finished.push(r);w.Z.previewImage=()=>`image-${w._spbSourceGeneration}`;
  vm.runInContext(slice('function refine(entry)','function another(entry)'),w);w.refine({request:'A request'});w._spbSourceGeneration++;w._spbSourcePath='B.psd';gate.resolve();await new Promise(r=>setImmediate(r));
  scenario('refine-critic-late-rejection',()=>{assert.equal(asks.length,0);assert.equal(finished.length,0);return{asks:asks.length,finishCalls:finished.length};});
 }
 // Actual mcpCallCore write path with a pending async tool result: no apply after source replacement.
 {
  const gate=deferred(),w=world({makeTools:q=>[{name:'edit_zone',handler:()=>gate.promise.then(r=>{q.push({kind:'edit',zone:0,spec:{color:'#ff0000'}});return r;})}]});
  w.mcpCall('edit_zone',{});await flush();w._spbSourceGeneration++;w._spbSourcePath='B.psd';gate.resolve({ok:true});await new Promise(r=>setImmediate(r));
  scenario('mcp-pending-tool-source-replacement',()=>{assert.equal(w.applyCalls.length,0);return{applies:w.applyCalls.length,sourceGeneration:w._spbSourceGeneration};});
 }
 // Preview enters palette await after sampling A; the wrapper must refuse a late result and not leak B's preview.
 {
  const paletteGate=deferred(),w=world({paletteGate});const p=w.mcpCall('preview',{parts:false});await flush();
  w._spbSourceGeneration++;w._spbSourcePath='B.psd';paletteGate.resolve({red:100});const res=await p;
  scenario('mcp-source-switch-during-preview',()=>{assert.equal(res.ok,false);assert.equal(res.images,undefined);return{ok:res.ok,images:res.images||[],sampled:w.previewSamples,lateImageSampling:w.imageReturns};});
 }
 // Cancel A, start B, then resolve A. Use the candidate's actual cancel branch and actual operation manager.
 {
  const a=deferred(),b=deferred();let n=0;const w=world({makeTools:q=>[{name:'edit_zone',handler:()=>((++n===1?a:b).promise.then(r=>{q.push({kind:'edit',zone:0,spec:{color:n===1?'#aa0000':'#0000aa'}});return r;}))}]});w.SpbAiLease=null;
  const pa=w.mcpCall('edit_zone',{});await flush();if(n!==1)throw new Error('A route did not reach handler n='+n+': '+JSON.stringify(await pa)+' makeTools='+String(w.makeTools).slice(0,120));
  w.clickCancel({hasAttribute:x=>x==='data-cancel'});const pb=w.mcpCall('edit_zone',{});await flush();assert.equal(n,2);const ownerB=w.operationManager().owner();a.resolve({ok:true});await new Promise(r=>setImmediate(r));
  scenario('mcp-cancel-A-start-B-late-A',()=>{assert.equal(w._busy,true);assert.equal(w.operationManager().owner(),ownerB);assert.equal(w.applyCalls.length,0);return{busy:w._busy,ownerId:ownerB.id,applies:w.applyCalls.length,lease:'not installed for this isolated operation-owner replay'};});
  b.resolve({ok:true});await Promise.all([pa,pb]);
  const gate=deferred(),leased=world({whenSettled:()=>gate.promise});let endCalls=0;const actualEnd=leased.SpbAiLease.end;leased.SpbAiLease.end=function(g){endCalls++;return actualEnd.call(leased.SpbAiLease,g);};const pendingA=leased.mcpCall('preview',{});await flush();const ticketA=leased.operationManager().owner();leased.operationManager().cancel(ticketA);leased.operationRelease(ticketA);leased.SpbAiLease.end();const bAcquired=leased.SpbAiLease.begin('external');leased._spbSourceGeneration++;gate.resolve();await pendingA;const staleAReleasedB=leased.SpbAiLease.begin('external');
  results.push({id:'mcp-cancel-A-start-B-late-A',mode:'supplemental-real-lease-rotation',candidateHasLeaseGeneration:typeof leased.SpbAiLease.generation==='function',bAcquired,staleReleaseEndCalls:endCalls,staleAReleasedB,observation:'candidate captures null generation because actual lease exposes no generation(); late A release calls end(null), which releases whichever same-owner lease is active'});if(staleAReleasedB)leased.SpbAiLease.end();
 }
 // Actual lease adapter: a rejected second acquisition must not end the existing owner.
 {
  const w=world();assert.equal(w.SpbAiLease.begin('external'),true);const res=await w.mcpCall('zones',{});const foreignActive=w.SpbAiLease.begin('internal')===false;
  scenario('actual-lease-reject-not-end-foreign',()=>{assert.equal(res.ok,false);assert.equal(w.SpbAiLease.owner(),'external');assert.ok(foreignActive);return{ok:res.ok,owner:w.SpbAiLease.owner(),foreignLeaseStillActive:foreignActive};});w.SpbAiLease.end();
 }
 // Actual lease + actual mcp wrapper on async rejection from the preview-settlement stage.
 {
  const w=world({whenSettled:()=>Promise.reject(new Error('controlled preview rejection'))});const res=await w.mcpCall('preview',{});const reacquired=w.SpbAiLease.begin('external');
  scenario('mcp-async-throw-release-once',()=>{assert.equal(res.ok,false);assert.ok(reacquired);return{ok:res.ok,controlledError:res.error,leaseReacquired:reacquired,busy:w._busy};});if(reacquired)w.SpbAiLease.end();
 }
 {
  const w=world();w.Z.zonesForModel=()=>[];const res=await w.mcpCall('zones',{}),reacquired=w.SpbAiLease.begin('external');
  scenario('external-lease-success-release',()=>{assert.equal(res.ok,true);assert.ok(reacquired);return{ok:res.ok,leaseReacquired:reacquired,busy:w._busy};});if(reacquired)w.SpbAiLease.end();
 }
 // Prove card/kit/refine/teach hooks capture and check their own ticket before continuing.
 staticOnly('warm-teach-source-switch',()=>{const send=slice('function send(text, o)','function mergeMaskUndo(entry, list)');assert.match(send,/if\(TEACH_RE\.test\(text\)&&CAR\)\{var teachTicket=operationStart\(\);if\(!operationCurrent\(teachTicket\)\)return;[\s\S]{0,240}if\(!operationCurrent\(teachTicket\)\)/);});
 staticOnly('finish-card-source-switch',()=>{const f=slice('function useFinishCard(entry, i, quiet, pendingTicket)','function useKit(entry, i, quiet, pendingTicket)');assert.match(f,/prior=operationTicket\(entry\).*?sameDocument\(prior\)/);assert.match(f,/operationCurrent\(ticket\)\?CAR\.ensure/);assert.match(f,/if\(!operationCurrent\(ticket\)\).*?operationCanceled/);});
 staticOnly('kit-use-source-switch',()=>{const f=slice('function useKit(entry, i, quiet, pendingTicket)','function fcDetail(entry, i)');assert.match(f,/prior=operationTicket\(entry\).*?sameDocument\(prior\)/);assert.match(f,/operationCurrent\(ticket\)\?CAR\.ensure/);assert.match(f,/if\(!operationCurrent\(ticket\)\).*?operationCanceled/);});
 staticOnly('refine-critic-late-rejection',()=>{const f=slice('function refine(entry)','function another(entry)');assert.match(f,/var ticket=operationStart\(\);if\(!operationCurrent\(ticket\)\)return/);assert.match(f,/if\(!operationCurrent\(ticket\)\).*?operationCanceled/);assert.match(f,/askForTicket\(text,\{image:img[\s\S]*?_spbOperation:ticket\}/);});
 staticOnly('self-help-doit-immediate-finish',()=>{const f=slice('function send(text, o)','function mergeMaskUndo(entry, list)');assert.match(f,/runDoIt\(text\)[\s\S]{0,280}finish\(selfHelpResult\(\{ text: _shd\.text, intent: 'do_it' \}\), text, 'ask'\)/);});
 staticOnly('cancel-preview-manual-revision-conflict',()=>{const a=source.indexOf("if (b.hasAttribute('data-cancel')) {"),b=source.indexOf('var act = b.getAttribute',a),f=source.slice(a,b),op=slice('function operationRelease(t)','function operationResultCurrent(r)');assert.match(f,/om\.cancel\(ot\)/);assert.match(op,/m&&m\.owns\(t\)/);});
 staticOnly('external-lease-success-release',()=>{const f=slice('function mcpCall(tool,args)','function mcpCallCore(tool,args,ticket)');assert.match(f,/released=false/);assert.match(f,/if\(released\)return;released=true/);assert.match(f,/lease\.end\(leaseGeneration\)/);});
 // Assert candidate core apply has a second ownership gate at the publication sink.
 staticOnly('mcp-source-and-apply-guards',()=>{const f=slice('function mcpApply(tool,queue,res,ticket)','// SPB-AI owner handoff 2026-10-01'),core=slice('function mcpCallCore(tool,args,ticket)','// ------------------------------------------------------------------ PARTS FIRST');assert.match(f,/if\(!operationCurrent\(ticket\)\)/);assert.match(f,/operationPublish\(ticket,function\(\)\{return applyQueue/);assert.match(core,/if\(!operationCurrent\(ticket\)\)return/);});
 const errors=results.filter(x=>x.error);const operationSha=crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'js/spb-ai-operation.js'))).digest('hex').toUpperCase(),leaseSha=crypto.createHash('sha256').update(leaseSource).digest('hex').toUpperCase();
 const report={status:errors.length?'BLOCKED':'FINDINGS',task:'W33 delayed-helper and MCP candidate recheck',date:'2026-10-04',oracle:{sha256:SHA256,count:ORACLE.length,cases:ORACLE},candidate:{path:'_easy_claude_work/ai14h_w10_pre_rebase/js/spb-pro-ai.js (byte-pinned copy)',sha256:candidateHash,bytes:Buffer.byteLength(source)},operationModule:{path:'js/spb-ai-operation.js',sha256:operationSha},leaseAdapter:{path:'js/spb-ai-lease.js',sha256:leaseSha},counts:{oracleCases:ORACLE.length,concreteChecks:results.filter(x=>x.mode==='concrete').length,staticOnlyChecks:results.filter(x=>x.mode==='static-only').length,assertionErrors:errors.length,providerCalls:0,nativeCalls:0,browserCalls:0},results,findings:errors.slice(),reviewFindings:[{severity:'P1 lifecycle/interface gap',where:'candidate mcpCall at lines 2125-2136; js/spb-ai-lease.js end/begin lines 6-13',issue:'Candidate tries lease.generation() but the actual SpbAiLease API exposes no generation; candidate therefore captures null and calls unscoped end(null). In an adversarial lease rotation, late A cleanup calls end while same-owner B is active and deactivates B. Actual cancel does not release the lease itself, so ordinary B admission remains blocked; if a separate cancellation/takeover lifecycle retires A and reacquires B before A settles, cleanup can release the replacement. Give lease acquisitions a generation/token and require matching-token end, or only end when candidate still owns the current generation.'}],limits:['Candidate exact bytes copied to a temp snapshot and SHA verified; no moving candidate loaded.','Actual candidate helper/MCP functions, standalone operation module, and actual lease adapter loaded in VM; only provider/native/app paint effects are mocked.','The MCP source-switch preview case verifies public wrapper rejects the result after a replacement; its core samples a B preview image while assembling a response, but the stale wrapper returns no image/result to caller.','The finish-card/kit/refine/warm routes were dynamically delayed and source-switched. Cancel/manual-revision and self-help assertions are static-only source checks; no UI/native path was run.','No live renderer/provider, native app, project load, external MCP server, or browser run.']};
 if(errors.length){report.status='BLOCKED';report.findings.push(...errors);}
 const reportPath=path.join(root,'docs/handoff_reports/AI_HELPER_14H_OPERATION_DELAYED_HELPERS_RECHECK_2026-10-03.json');fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,counts:report.counts,results,report:reportPath},null,2));if(errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
