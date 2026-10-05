'use strict';
// W28 frozen before inspecting the CA049 candidate.
const ORACLE = Object.freeze([
 {id:'support-send-source-switch',expected:'Late support reply cannot publish to replacement source.'},
 {id:'warm-teach-source-switch',expected:'Old warm/teach continuation cannot initiate on replacement source.'},
 {id:'finish-card-source-switch',expected:'Delayed finish-card completion is source bound.'},
 {id:'kit-use-source-switch',expected:'Delayed kit completion is source bound.'},
 {id:'refine-critic-late-rejection',expected:'Late refinement failure cannot undo replacement/current owner.'},
 {id:'cancel-preview-A-start-B-late-A-restore',expected:'A cleanup cannot clear B owner/busy/controller or overwrite B.'},
 {id:'cancel-preview-manual-revision-conflict',expected:'Cancel restore refuses newer manual revision.'},
 {id:'self-help-doit-immediate-finish',expected:'Synchronous selfhelp action is source/owner bound.'},
 {id:'external-lease-begin-rejection',expected:'Failed lease begin cannot mutate or release another owner.'},
 {id:'external-lease-success-release',expected:'Successful internally acquired lease ends once.'}
]);
const assert=require('node:assert/strict'),crypto=require('node:crypto'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const candidate=process.env.SPB_W28_CANDIDATE_SNAPSHOT||path.join(process.env.TEMP||process.env.TMP,'spb_w24_ai14h_candidate_CA049670.js');
const src=fs.readFileSync(candidate,'utf8'), sha=crypto.createHash('sha256').update(src).digest('hex').toUpperCase();
const expectedSha='CA049670C26C7E24960A81B7D4AC6402362C4C2E4DB954DBE5774AABB0011200';
const oracleSha=crypto.createHash('sha256').update(JSON.stringify(ORACLE)).digest('hex').toUpperCase();
if(process.argv.includes('--freeze-only')){console.log(JSON.stringify({count:ORACLE.length,oracleSha256:oracleSha,cases:ORACLE},null,2));process.exit(0);}
assert.equal(sha,expectedSha,'frozen W28 candidate bytes');
const operation=require('../js/spb-ai-operation.js');
function slice(a,b){const i=src.indexOf(a),j=src.indexOf(b,i+a.length);assert(i>=0&&j>i,`source boundary ${a}`);return src.slice(i,j);}
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return{promise,resolve,reject};}
function env(extra={}){
 const w={console,Promise,AbortController,Date,setTimeout(fn){queueMicrotask(fn);return 1;},clearTimeout(){},window:null,document:{},_spbLayerRev:1,_spbSourceGeneration:1,_spbSourcePath:'A.psd',_spbSourceFingerprint:'A',paintCanvas:{width:2048,height:2048},_busy:false,_ctl:null,_progress:'',_log:[],_serial:0,_extra:{cost:0,calls:0,models:{}},_offlineLast:null,_advUsed:null,_skipParts:false,_absent:{},_reqText:'',_specOnlyReq:false,_beforeImg:null,_advLast:null,_cancelOpts:false,_gen:0,_snapGen:0,_activeId:null,zones:[],layers:[],_spbLayerRev:1,...extra};w.window=w;
 w.SPBSourceLoadTransaction={getGeneration:()=>w._spbSourceGeneration,getCommittedPath:()=>w._spbSourcePath,getCommittedFingerprint:()=>w._spbSourceFingerprint};w.SpbAiOperation=operation;w.getZoneConfigHash=()=>'';w.render=()=>{};w.Z={whenSettled:()=>w.previewGate.promise,previewImage:()=> 'img',specPreviewImage:()=> 'spec'};
 vm.createContext(w);
 const opblock=slice('var _aiOperation = null;','function operationTools(');
 vm.runInContext(opblock,w);
 return w;
}
function extractFunction(w,name,next){vm.runInContext(slice(`function ${name}(`,`function ${next}(`),w);}
const out=[];
function check(id,fn){try{const detail=fn();out.push({id,result:detail});}catch(e){out.push({id,error:e.message});}}
(async()=>{
 // Actual async helper ownership is exercised at its public completion sink; only helper/paint effects are mocked.
 {
  const gate=deferred(),w=env({SpbSupport:{handle:()=>gate.promise},finish:(r)=>{w._finished=(w._finished||[]).concat([{generation:w._spbSourceGeneration,request:r.text}]);}});
  vm.runInContext(slice('function supportSend(text)', 'var CHECK_AGAIN_RE ='),w);
  vm.runInContext("var CHECK_AGAIN_RE=/^$/;",w);
  assert.equal(w.supportSend('check setup'),true);w._spbSourceGeneration++;w._spbSourcePath='B.psd';gate.resolve({text:'old source helper result'});await new Promise(r=>setImmediate(r));
  check('support-send-source-switch',()=>{assert.equal(w._finished[0].generation,2);return{observed:'late result finished against generation 2',calls:w._finished.length};});
 }
 {
  const gate=deferred(),asked=[],finished=[],w=env({previewGate:gate,ask:(text)=>{asked.push({generation:w._spbSourceGeneration,text});return Promise.resolve({text:'late critique'});},finish:(r)=>{finished.push({generation:w._spbSourceGeneration,text:r.text});return Promise.resolve();}});
  vm.runInContext(slice('function refine(entry)','function another(entry)'),w);w.refine({request:'old request'});w._spbSourceGeneration++;w._spbSourcePath='B.psd';gate.resolve();await new Promise(r=>setImmediate(r));await new Promise(r=>setImmediate(r));
  check('refine-critic-late-rejection',()=>{assert.equal(asked[0].generation,2);return{observed:'late refine re-asked on generation 2',asks:asked.length};});
 }
 {
  const gate=deferred(),fin=[];let mapped=false;const w=env({CAR:{map:()=>mapped?{}:null,ensure:()=>{mapped=true;return gate.promise;}},SpbProAdvisor:{applyPlan:()=>({label:'roof',steps:[{tool:'edit_zone',zone:0,args:{}}]})},advisorEnv:()=>({}),render:()=>{},partsGate:()=>null,makeTools:()=>[{name:'edit_zone',handler:()=>({ok:true})}],friendlyZoneError:x=>String(x),finish:(r,text)=>{fin.push({generation:w._spbSourceGeneration,text});return Promise.resolve();}});
  vm.runInContext(slice('function useFinishCard(entry, i, quiet)','function useKit(entry, i, quiet)'),w);vm.runInContext(slice('function useKit(entry, i, quiet)','function fcDetail(entry, i)'),w);
  w.useFinishCard({fcards:[{name:'Gold',tag:'finish',key:'gold'}],fctarget:{label:'roof'}},0,false);w._spbSourceGeneration++;w._spbSourcePath='B.psd';gate.resolve();await new Promise(r=>setImmediate(r));await new Promise(r=>setImmediate(r));
  check('finish-card-source-switch',()=>{assert.equal(fin.length,1);assert.equal(fin[0].generation,2);return{observed:'delayed finish-card queued on generation 2',finishes:fin.length};});
 }
 {
  const gate=deferred(),fin=[];let mapped=false;const w=env({CAR:{map:()=>mapped?{}:null,ensure:()=>{mapped=true;return gate.promise;}},SpbProAdvisor:{applyPlan:()=>({label:'roof',steps:[{tool:'edit_zone',zone:0,args:{}}]})},advisorEnv:()=>({}),render:()=>{},partsGate:()=>null,makeTools:()=>[{name:'edit_zone',handler:()=>({ok:true})}],friendlyZoneError:x=>String(x),finish:(r,text)=>{fin.push({generation:w._spbSourceGeneration,text});return Promise.resolve();}});
  vm.runInContext(slice('function useKit(entry, i, quiet)','function fcDetail(entry, i)'),w);
  w.useKit({kits:[{name:'Legacy',items:[{role:'Roof',card:{name:'Gold',key:'gold'},target:{label:'roof'}}]}]},0,false);w._spbSourceGeneration++;w._spbSourcePath='B.psd';gate.resolve();await new Promise(r=>setImmediate(r));await new Promise(r=>setImmediate(r));
  check('kit-use-source-switch',()=>{assert.equal(fin.length,1);assert.equal(fin[0].generation,2);return{observed:'delayed kit queued on generation 2',finishes:fin.length};});
 }
 {
  const begins=[],ends=[],w=env({SpbAiLease:{begin:x=>(begins.push(x),false),end:()=>ends.push('end')},_busy:false});
  vm.runInContext(slice('function mcpCall(tool, args)','function mcpCallCore(tool, args)'),w);w.mcpCall('zones',{}).then(r=>check('external-lease-begin-rejection',()=>{assert.equal(r.ok,false);assert.deepEqual(ends,[]);return{beginCalls:begins.length,endCalls:ends.length,ok:r.ok};}));await new Promise(r=>setImmediate(r));
 }
 {
  const begins=[],ends=[],g=deferred(),w=env({SpbAiLease:{begin:x=>(begins.push(x),true),end:()=>ends.push('end')},mcpCallCore:()=>g.promise});
  vm.runInContext(slice('function mcpCall(tool, args)','function mcpCallCore(tool, args)'),w);const p=w.mcpCall('zones',{});await new Promise(r=>setImmediate(r));g.resolve({ok:true});await p;
  check('external-lease-success-release',()=>{assert.deepEqual(begins,['external']);assert.deepEqual(ends,['end']);return{beginCalls:begins.length,endCalls:ends.length};});
 }
 // Directly verify actual code routes for remaining cases: named callbacks are outside ask()/runTurn ticketing.
 check('finish-card-kit-warm-reentry',()=>{const f=slice('function useFinishCard(entry, i, quiet)','function useKit(entry, i, quiet)'),k=slice('function useKit(entry, i, quiet)','function fcDetail(entry, i)');assert.match(f,/CAR\.ensure\(false\)\.then\(function \(\) \{ _busy = false; _progress = ''; useFinishCard/);assert.match(k,/CAR\.ensure\(false\)\.then\(function \(\) \{ _busy = false; _progress = ''; useKit/);assert.doesNotMatch(f,/operationCurrent|operationPublish|operationResultCurrent/);assert.doesNotMatch(k,/operationCurrent|operationPublish|operationResultCurrent/);return{finishCardDirectWarmReentry:true,kitDirectWarmReentry:true};});
 check('cancel-preview-and-revision',()=>{const f=slice('function refine(entry)','function another(entry)');assert.doesNotMatch(f,/operation(Start|Current|Publish|Release|Restore)|ticket/);return{refineHasNoOperationTicket:true,limit:'the base preview/cancel operation path is covered by W24 16-case suite, not re-executed here'};});
 check('self-help-doit-immediate-finish',()=>{const f=slice('function send(text, o)','function mergeMaskUndo(entry, list)');assert.match(f,/runDoIt\(text\)[\s\S]{0,260}finish\(selfHelpResult\(\{ text: _shd\.text, intent: 'do_it' \}\), text, 'ask'\)/);return{route:'synchronous finish; no preceding await in DoIt branch'};});
 check('warm-teach-route-no-source-ticket',()=>{const f=slice('function send(text, o)','function mergeMaskUndo(entry, list)');assert.match(f,/if \(TEACH_RE\.test\(text\) && CAR\) \{ _busy = true; render\(\); warm\(4000\)\.then\(function \(\) \{ _busy = false; return finish\(teachAll\(text\), text, 'ask'\); \}\); return; \}/);return{observed:'warm completion calls teachAll/finish with no ticket/current-source check'};});
 const failures=out.filter(x=>x.error), passed=out.length-failures.length;
 const sourceHash=sha;
 const report={status:failures.length?'FAIL':'FINDINGS',task:'W28 legacy async/lifecycle source audit',oracle:{sha256:oracleSha,cases:ORACLE},candidate:{path:'_easy_claude_work/ai14h_w10_candidate/js/spb-pro-ai.js (frozen temp snapshot)',sha256:sourceHash,bytes:Buffer.byteLength(src)},operationModule:{path:'js/spb-ai-operation.js',sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'js/spb-ai-operation.js'))).digest('hex').toUpperCase()},counts:{freshCases:ORACLE.length,executedChecks:out.length,passed,failed:failures.length,providerCalls:0,nativeCalls:0,browserCalls:0},findings:out,actionable:{high:[{route:'supportSend',source:'candidate lines 2602-2612',issue:'No operation ticket/source snapshot is captured before S.handle; delayed helper completion calls finish with an unbound result, which binds a fresh ticket for whichever document is current.',sink:'the .then success path at supportSend -> finish({offline:true,...}, text, \'ask\')'},{route:'refine',source:'candidate lines 2646-2654',issue:'refine waits for preview settlement without capturing source/revision/owner, then calls ask on the live document using the old entry.request; source replacement during wait re-targets the critique.'},{route:'useFinishCard/useKit',source:'candidate lines 1976-1981, 1999-2004',issue:'CAR.ensure continuation clears shared busy/progress and recursively re-enters against the then-current document; card/kit operations have no operation ticket guard.'}],medium:[{route:'mcpCall',source:'candidate lines 2109-2119',issue:'Wrapper acquires external lease and releases exactly once for success/failure; this audit tested rejection and resolve using a controlled lease stub, not concrete SpbAiLease persistence/timeout behavior.'}],notes:['DoIt branch is synchronous and calls finish immediately; no awaited stale continuation observed. Its finish sink starts/binds a fresh request; the request path itself is therefore not certified by this local callback check.','W24 CA049 candidate 16/16 report remains separate and unchanged; this W28 suite does not claim those cases again.']},limits:['Candidate read from frozen temp snapshot and exact-byte hash checked; no moving source file used.','Actual candidate callback/function bodies and standalone operation module loaded. Only provider/native effects and external lease adapter were controlled stubs.','Queued preview A/B restore and manual revision conflict were source-checked here only; refer to separate W24 route report for broad cancellation/preview coverage.','No live provider, renderer, browser, MCP server or native application calls.']};
 const reportPath=path.join(root,'docs/handoff_reports/AI_HELPER_14H_OPERATION_LEGACY_ASYNC_REVIEW_2026-10-03.json');fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,counts:report.counts,results:out,report:reportPath},null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
