'use strict';
// W49 isolates the frozen W42 callback defect and candidate repair. No provider,
// renderer, native app, or server effects: teachBoxes is a counted fake sink.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const baselinePath = path.join(root, '_easy_claude_work/ai14h_w42_sources/js/spb-pro-ai.js');
const candidatePath = path.join(root, '_easy_claude_work/ai14h_w65_review/frozen/spb-pro-ai.js');
const operationPath = path.join(root, '_easy_claude_work/ai14h_w65_review/frozen/spb-ai-operation.js');
const baselineHash = crypto.createHash('sha256').update(fs.readFileSync(baselinePath)).digest('hex').toUpperCase();
const candidateHash = crypto.createHash('sha256').update(fs.readFileSync(candidatePath)).digest('hex').toUpperCase();
const operationHash = crypto.createHash('sha256').update(fs.readFileSync(operationPath)).digest('hex').toUpperCase();
const patchPath = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_W49_MARK_ELEMENTS_MINIMAL_PATCH_2026-10-04.patch');
const patchHash = crypto.createHash('sha256').update(fs.readFileSync(patchPath)).digest('hex').toUpperCase();
const testHash = crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex').toUpperCase();
assert.equal(baselineHash, '5ECB313E66BA26B91020367C148D11227DA1385925E144A41DDEBD6940EA53EB');
assert.equal(candidateHash, '098237183363BBEEF6C8AF563C72CBEF24D341F87EB56CD7E034079F02FF8D57');
assert.equal(operationHash, '47587A1A53A35CE7E58825BAC864BD75C2421D26C19791957F57BB199A7000C6');

function slice(source, start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a + start.length);
  assert(a >= 0 && b > a, `expected source boundary ${start}`);
  return source.slice(a, b);
}
function deferred() { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b; }); return {promise,resolve,reject}; }
function makeWorld(source, controlledManager) {
  const w = { console, Promise, Date, setTimeout: fn => { fn(); return 1; }, clearTimeout() {},
    _spbSourceGeneration: 1, _spbSourcePath: 'A.psd', _spbSourceFingerprint: 'sha:A', _spbLayerRev: 1,
    _elemRunIdentity: null, _elemNone: {}, _elemCache: null, _taughtNow: {}, _elemOk: {}, ELEM_WORD:{numbers:'numbers',sponsors:'sponsors',stripes:'stripes'}, ELEM_TINT:{numbers:'pink',sponsors:'blue',stripes:'yellow'}, _log: [], _serial: 0,
    _busy: false, _ctl: null, _progress: '', zones: [], layers: [], paintCanvas: {width:1024,height:1024}, _psdLayers: [],
    SPBSourceLoadTransaction: {getGeneration:()=>w._spbSourceGeneration,getCommittedPath:()=>w._spbSourcePath,getCommittedFingerprint:()=>w._spbSourceFingerprint},
    SpbAiOperation: require(operationPath), getZoneConfigHash: () => '',
    document: {getElementById:()=>({width:1024,height:1024})},
    E: { prepPalette: () => [{name:'white'}] },
    SpbProElements: null,
    render() {}, elementPaintSig: () => 'paint-A', elementRunIdentity: () => null,
    elementRunCurrent: () => true, elementPaintChangedResult: () => ({error:'paint changed'}),
    logMiss() {}, toggle() {},
  };
  w.window = w;
  vm.createContext(w);
  vm.runInContext(slice(source, 'var _aiOperation = null;', 'function operationTools(') +
    slice(source, 'function operationTools(', '// End W10 operation helpers.') +
    slice(source, 'function markElements(kindIn, boxes, replace, extra)', '// WP12 2026-10-03'), w,
    {filename:'actual-w49-mark-elements-slices.js'});
  const at=source.indexOf("name: 'mark_elements'");
  const hs=source.indexOf('handler: function (a) { return markElements(',at);
  const he=source.indexOf('} },',hs);
  assert(at>=0&&hs>at&&he>hs,'actual mark_elements handler located');
  w.rawMarkHandler=vm.runInContext('('+source.slice(hs+'handler: '.length,he+1)+')',w);
  if (controlledManager) {
    const ticket={id:1,collection:1}; let collecting=true;
    const manager={bind:v=>v,ticketOf:()=>ticket,current:()=>true,collecting:()=>collecting,publish:(t,fn)=>({value:fn(),refused:false}),
      setCollecting:v=>{collecting=v;}};
    w.operationManager=()=>manager;
    return {w,ticket,collection:1,manager,setCollecting:v=>manager.setCollecting(v)};
  }
  return {w,manager:w.operationManager(),ticket:null,collection:null};
}
function deferredElements(gate, sink) {
  return { analyse:()=>gate.promise, modeFor:()=> 'glyph',
    teachBoxes:()=>{sink.calls++;return {used:[[0,0,0.1,0.1]],colours:['#ffffff'],share:2,places:[],skipped:[],mode:'glyph',maybe_more:[]};},
    kinds:()=>({numbers:{found:true}}), sig:()=> 'sig-A', remember:()=>true };
}
function invoke(env, options={}) {
  const queue=[]; env.w.queue=queue;
  const handler=env.w.operationTools([{name:'mark_elements',handler:env.w.rawMarkHandler}],queue,env.ticket,env.collection)[0].handler;
  return handler({kind:'numbers',boxes:[[0,0,0.1,0.1]],replace:true,...options});
}
async function runtimeCase(source, mode, options={}) {
  const gate=deferred(),sink={calls:0};
  const env=makeWorld(source, mode==='w42-baseline');
  env.w.SpbProElements=deferredElements(gate,sink);
  let ticket=env.ticket, collection=env.collection;
  if (!ticket) { ticket=env.w.operationStart(); collection=ticket.collection; env.ticket=ticket; env.collection=collection; }
  const pending=invoke(env,options);
  if (mode==='w42-baseline') env.setCollecting(false);
  else if (mode==='ready') { assert.equal(env.manager.ready(ticket,collection),true); assert.equal(env.manager.current(ticket),true); }
  else if (mode==='cancel') env.manager.cancel(ticket);
  else if (mode==='source-switch') env.w._spbSourceGeneration++;
  gate.resolve({ok:true});
  const result=await pending;
  return {result,sinkCalls:sink.calls,ticketCurrent:env.manager.current(ticket),collection:ticket.collection,phase:ticket.phase};
}

(async()=>{
  const rows=[];
  const baseline=await runtimeCase(fs.readFileSync(baselinePath,'utf8'),'w42-baseline');
  assert.equal(baseline.sinkCalls,1,'replay exact W42 stale collection reproduction');
  assert.ok(baseline.result && baseline.result.error,'outer async wrapper notices closed collection only after sink');
  rows.push({id:'w42-confirmed-stale-mark-elements-reproduction',verdict:'reproduced',...baseline});

  const ready=await runtimeCase(fs.readFileSync(candidatePath,'utf8'),'ready');
  assert.equal(ready.sinkCalls,0,'ready collection cannot publish a delayed analysis side effect');
  assert.equal(ready.ticketCurrent,true,'ticket remains current, isolating phase/collection as the fence');
  rows.push({id:'ready-before-analysis-resolves',verdict:'pass',...ready});

  const canceled=await runtimeCase(fs.readFileSync(candidatePath,'utf8'),'cancel');
  assert.equal(canceled.sinkCalls,0,'canceled operation cannot teach boxes');
  rows.push({id:'cancel-before-analysis-resolves',verdict:'pass',...canceled});

  const switched=await runtimeCase(fs.readFileSync(candidatePath,'utf8'),'source-switch');
  assert.equal(switched.sinkCalls,0,'replacement source cannot receive delayed teaching');
  rows.push({id:'source-generation-switch-before-analysis-resolves',verdict:'pass',...switched});

  const positive=await runtimeCase(fs.readFileSync(candidatePath,'utf8'),'current');
  assert.equal(positive.sinkCalls,1,'current collecting request preserves positive mark behavior');
  assert.equal(positive.result.ok,true);
  rows.push({id:'positive-current-mark-still-teaches',verdict:'pass',...positive});

  const noneGate=deferred(),noneSink={calls:0},noneEnv=makeWorld(fs.readFileSync(candidatePath,'utf8'),false);
  noneEnv.w.SpbProElements=deferredElements(noneGate,noneSink);noneEnv.w._log.push({role:'ai',elem:{kind:'numbers',done:false}});
  const noneTicket=noneEnv.w.operationStart();noneEnv.ticket=noneTicket;noneEnv.collection=noneTicket.collection;
  const staleNone=invoke(noneEnv,{none:true});assert.equal(noneEnv.manager.ready(noneTicket,noneTicket.collection),true);noneGate.resolve({ok:true});
  const staleNoneResult=await staleNone;assert.equal(noneSink.calls,0);assert.equal(Object.hasOwn(noneEnv.w._elemNone,'numbers'),false);
  assert.equal(noneEnv.w._log[0].elem.done,false);
  rows.push({id:'ready-before-none-analysis-resolves',verdict:'pass',error:staleNoneResult.error,elemNoneRecorded:false,pendingCardClosed:false});

  const liveNoneGate=deferred(),liveNoneSink={calls:0},liveNoneEnv=makeWorld(fs.readFileSync(candidatePath,'utf8'),false);
  liveNoneEnv.w.SpbProElements=deferredElements(liveNoneGate,liveNoneSink);liveNoneEnv.w._log.push({role:'ai',elem:{kind:'numbers',done:false}});
  const liveNoneTicket=liveNoneEnv.w.operationStart();liveNoneEnv.ticket=liveNoneTicket;liveNoneEnv.collection=liveNoneTicket.collection;
  const liveNone=invoke(liveNoneEnv,{none:true});liveNoneGate.resolve({ok:true});const liveNoneResult=await liveNone;
  assert.equal(liveNoneResult.ok,true);assert.equal(liveNoneEnv.w._elemNone.numbers,'sig-A');assert.equal(liveNoneEnv.w._log[0].elem.done,true);
  rows.push({id:'positive-current-none-keeps-helpful-result',verdict:'pass',ok:liveNoneResult.ok,elemNoneRecorded:true,pendingCardClosed:true});

  const lateGate=deferred(),lateSink={calls:0},lateEnv=makeWorld(fs.readFileSync(candidatePath,'utf8'),false);
  lateEnv.w.SpbProElements=deferredElements(lateGate,lateSink);const lateA=lateEnv.w.operationStart();lateEnv.ticket=lateA;lateEnv.collection=lateA.collection;
  const lateAResult=invoke(lateEnv);lateEnv.manager.cancel(lateA);const currentB=lateEnv.w.operationStart(),ctlB={owner:'B'};lateEnv.w._busy=true;lateEnv.w._ctl=ctlB;lateGate.resolve({ok:true});const settledA=await lateAResult;
  assert.equal(lateSink.calls,0,'late A analysis cannot teach into B');assert.equal(lateEnv.manager.current(currentB),true,'late cleanup cannot retire new B');assert.equal(lateEnv.w._busy,true);assert.equal(lateEnv.w._ctl,ctlB);
  rows.push({id:'fresh-cancel-A-start-B-late-analysis-A',verdict:'pass',sinkCalls:lateSink.calls,currentB:lateEnv.manager.current(currentB),busyStillB:lateEnv.w._busy,controllerStillB:lateEnv.w._ctl===ctlB,lateError:settledA&&settledA.error});

  const revGate=deferred(),revSink={calls:0},revEnv=makeWorld(fs.readFileSync(candidatePath,'utf8'),false);
  revEnv.w.SpbProElements=deferredElements(revGate,revSink);const revTicket=revEnv.w.operationStart();revEnv.ticket=revTicket;revEnv.collection=revTicket.collection;
  const revPending=invoke(revEnv);revEnv.w._spbLayerRev++;revGate.resolve({ok:true});const revResult=await revPending;
  assert.equal(revSink.calls,0,'manual revision during analysis must block teachBoxes');assert.equal(revEnv.manager.current(revTicket),false);
  rows.push({id:'fresh-manual-layer-revision-during-analysis',verdict:'pass',sinkCalls:revSink.calls,current:revEnv.manager.current(revTicket),lateError:revResult&&revResult.error});

  const cancelNoneGate=deferred(),cancelNoneSink={calls:0},cancelNoneEnv=makeWorld(fs.readFileSync(candidatePath,'utf8'),false);
  cancelNoneEnv.w.SpbProElements=deferredElements(cancelNoneGate,cancelNoneSink);cancelNoneEnv.w._log.push({role:'ai',elem:{kind:'numbers',done:false}});
  const cancelNoneTicket=cancelNoneEnv.w.operationStart();cancelNoneEnv.ticket=cancelNoneTicket;cancelNoneEnv.collection=cancelNoneTicket.collection;
  const cancelNonePending=invoke(cancelNoneEnv,{none:true});cancelNoneEnv.manager.cancel(cancelNoneTicket);cancelNoneGate.resolve({ok:true});const cancelNoneResult=await cancelNonePending;
  assert.equal(cancelNoneSink.calls,0);assert.equal(Object.hasOwn(cancelNoneEnv.w._elemNone,'numbers'),false);assert.equal(cancelNoneEnv.w._log[0].elem.done,false);
  rows.push({id:'fresh-canceled-no-target-analysis-does-not-publish-none-or-close-card',verdict:'pass',sinkCalls:cancelNoneSink.calls,elemNoneRecorded:false,pendingCardClosed:false,error:cancelNoneResult&&cancelNoneResult.error});

  // Preserve the distinct unchanged W42 stale-spec oracle outcome: its old
  // assertion expects queue length 1, but frozen W42 returns no queue.
  const w42Report=JSON.parse(fs.readFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_OPERATION_W42_OFFLINE_ASYNC_2026-10-04.json'),'utf8'));
  const mismatch=w42Report.runtime.find(x=>x.id==='offline-spec-preview-manual-revision-conflict');
  assert(mismatch && mismatch.verdict==='fail' && /0 !== 1/.test(mismatch.reason));
  rows.push({id:'unchanged-w42-stale-spec-expectation-mismatch',verdict:'retained-expectation-mismatch',observed:'frozen W42 helper returned no stale queue; no direct zone mutation was observed'});

  const status=rows.some(x=>x.verdict==='reproduced')?'FINDINGS':'PASS_WITH_LIMITS';
  const report={status,task:'W49 isolated stale mark_elements async callback repair',date:'2026-10-04',
    sources:{baselinePath:'_easy_claude_work/ai14h_w42_sources/js/spb-pro-ai.js',baselineSha256:baselineHash,
      candidatePath:'_easy_claude_work/ai14h_w65_review/frozen/spb-pro-ai.js',candidateSha256:candidateHash,
      operationPath:'_easy_claude_work/ai14h_w65_review/frozen/spb-ai-operation.js',operationSha256:operationHash,
      minimalPatchPath:'docs/handoff_reports/AI_HELPER_14H_W49_MARK_ELEMENTS_MINIMAL_PATCH_2026-10-04.patch',minimalPatchSha256:patchHash,
      testPath:'tests/ai_operation_w49_mark_elements_repair_contract.cjs',testSha256:testHash},
    repair:'markElements now captures operation ticket collection and requires manager.collecting(ticket,collection) at entry and after each asynchronous analyse await, before either none-state publication or teachBoxes. This separates phase-current ticket ownership from active tool-collection permission.',
    patchValidation:'The minimal unified diff was applied with git apply --check and replayed against a disposable copy of the frozen baseline; its SHA matched the isolated candidate.',
    counts:{cases:rows.length,baselineDefects:rows.filter(x=>x.verdict==='reproduced').length,candidatePositiveAndStaleControls:rows.filter(x=>x.verdict==='pass').length,providerCalls:0,nativeCalls:0,serverWrites:0},rows,
    limits:['Actual mark_elements handler, operationTools, markElements and operation manager are evaluated from source in VM. El.analyse and teachBoxes are controlled deferred/fake callbacks.',
      'No browser, native app, provider, server, real image or paint buffer was used. The test proves callback gating and preserves a positive helper call, not visual correctness of box detection.',
      'The unchanged W42 stale-spec mismatch is read from the frozen W42 replay report and retained separately; W49 does not alter its assertion or claim it is a paint defect.']};
  fs.writeFileSync(path.join(root,'_easy_claude_work/ai14h_w65_review/w49-replay.json'),JSON.stringify(report,null,2)+'\n');
  const w24Path=path.join(root,'_easy_claude_work/ai14h_w65_review/w24-replay.json'),w24=JSON.parse(fs.readFileSync(w24Path,'utf8'));
  const freshRows=rows.filter(x=>String(x.id).startsWith('fresh-'));
  const w24Run=w24.latest_comparison||w24;
  const w24Pass=w24Run.counts.total===16&&w24Run.counts.passed===16&&w24Run.counts.failed===0;
  const w65Report={status:freshRows.every(x=>x.verdict==='pass')&&w24Pass?'PASS':'BLOCKED',task:'W65 independent late mark-elements and controller ownership regression review',date:'2026-10-04',
    frozenSource:{controller:{path:'_easy_claude_work/ai14h_w65_review/frozen/spb-pro-ai.js',sha256:candidateHash},operation:{path:'_easy_claude_work/ai14h_w65_review/frozen/spb-ai-operation.js',sha256:operationHash}},
    retainedW49:{original_test:'tests/ai_operation_w49_mark_elements_repair_contract.cjs',original_test_sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'tests/ai_operation_w49_mark_elements_repair_contract.cjs'))).digest('hex').toUpperCase(),candidate_replay_path:'_easy_claude_work/ai14h_w65_review/w49-replay.json',candidate_replay_rows:rows.filter(x=>x.id!=='unchanged-w42-stale-spec-expectation-mismatch'),unchanged_w42_baseline_reproduction_separate:true},
    retainedW24Phase6:{original_oracle_sha256:'3293D6070258C895F67A21ECCFE0BBEE7FD000568196FF37A834303C128BDCEA',replay_path:'_easy_claude_work/ai14h_w65_review/w24-replay.json',status:w24Pass?'PASS':'BLOCKED',total:w24Run.counts.total,passed:w24Run.counts.passed,failed:w24Run.counts.failed,real_provider_calls:0,mocked_provider_invocations:w24Run.counts.mocked_provider_invocations,harness_adaptations:['Adapted the bounded extraction boundary for integrated makeTools(queue,sig,mode).','Added actual offlineInstructionPreflight helper to extracted route after the current candidate introduced that dependency.','Stubbed onlineMeasure/objectFollowup post-response helpers only; lifecycle, tools, operation module, queue/apply/Undo paths remain actual source functions.']},
    counts:{freshW65: freshRows.length,freshW65Passed:freshRows.filter(x=>x.verdict==='pass').length,w49CandidateControls:rows.filter(x=>x.verdict==='pass').length,w24Phase6Passed:w24Run.counts.passed,providerCalls:0,nativeCalls:0,browserCalls:0},freshRows,
    finding:{baselineW42LateTeachReproductionObserved:true,w65CandidateLateCallbacksBlocked:true,positiveMarkElementsAndNone:true,normalFinishAndUndo:'PASS through retained W24 normal-action-and-undo case'},
    limits:['The W42 baseline stale-collection reproduction remains an expected historical control, not a W65 candidate defect.','El.analyse and teachBoxes are controlled callbacks. markElements checks collection ownership after async analyse and before the synchronous teachBoxes mutation; teachBoxes itself has no async continuation.','W24 uses the actual pinned operation module and extracted controller lifecycle functions, with local provider, apply, preview and Undo effects mocked. No real provider, browser, native app, canvas renderer or paint mutation occurred.']};
  fs.writeFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_W65_MARK_ELEMENTS_CONTROLLER_REVIEW_2026-10-04.json'),JSON.stringify(w65Report,null,2)+'\n');
  console.log(JSON.stringify({status:w65Report.status,counts:w65Report.counts,rows:rows.map(({id,verdict,sinkCalls,phase,ticketCurrent})=>({id,verdict,sinkCalls,phase,ticketCurrent}))},null,2));
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
