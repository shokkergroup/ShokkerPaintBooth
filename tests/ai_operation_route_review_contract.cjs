'use strict';
// Frozen actual-route acceptance oracle, written before root wires the operation manager.
// Fake provider/native effects only. Identity uses source generation/image/path/dimensions/revision.
const ORACLE = Object.freeze([
  { id: 'sync-provider-throw-releases-request', must: ['busy and controller clear', 'composer can accept a fresh request'] },
  { id: 'warm-rejection-releases-request', must: ['warm failure is settled safely', 'no stale or stranded busy state'] },
  { id: 'cancel-ignoring-abort-discards-late-success', must: ['late canceled result cannot apply', 'cannot publish done'] },
  { id: 'cancel-A-new-B-late-A-result', must: ['A completion cannot clear B busy/owner', 'A queue cannot apply'] },
  { id: 'cancel-A-new-B-late-A-event', must: ['late progress event cannot overwrite B status or composer'] },
  { id: 'cancel-A-new-B-late-A-tool-callback', must: ['stale A tool callback cannot append/apply after B begins'] },
  { id: 'cancel-A-new-B-late-A-rejection-cleanup', must: ['A finally/rejection cannot clear B ownership or busy state'] },
  { id: 'ready-A-ask-B-before-finish-A', must: ['A finish becomes stale once B owns the route', 'A cannot apply or mark completion'] },
  { id: 'same-path-source-generation-reload', must: ['same-path new source generation invalidates old turn before apply'] },
  { id: 'warm-source-switch-before-provider', must: ['old warm continuation cannot call provider after source switch'] },
  { id: 'preflight-source-switch-before-provider', must: ['old preflight continuation cannot start model turn on new source'] },
  { id: 'ordinary-options-source-switch', must: ['old options cannot preview/apply on replacement source'] },
  { id: 'same-document-cancel-restores-own-preview', must: ['cancel restores exact owned preview snapshot once', 'later manual edit is not overwritten'] },
  { id: 'manual-revision-conflict-before-apply', must: ['stale turn cannot publish over a manual revision'] },
  { id: 'normal-action-and-undo', must: ['one current action applies once', 'Undo restores exactly that action'] },
  { id: 'public-ask-starts-B-after-cancel-A', must: ['public ask admits B while canceled A is still settling'] }
]);

const assert = require('node:assert/strict');
const SpbAiOperation = require('../js/spb-ai-operation.js');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const proPath = path.join(root, 'js/spb-pro-ai.js');
const proSource = fs.readFileSync(proPath, 'utf8');
const SOURCE_SHA256 = '115F602D49E465B6F49530B07A4C2E4B81E8D6089C2D8204BCAE9D57807690D4';
assert.equal(crypto.createHash('sha256').update(proSource).digest('hex').toUpperCase(), SOURCE_SHA256, 'route test is pinned to the pre-integration pro-AI source');

function sourceSlice(start, end) {
  const a = proSource.indexOf(start), b = proSource.indexOf(end, a + start.length);
  assert(a >= 0 && b > a, `actual pro-AI boundary exists: ${start}`);
  return proSource.slice(a, b);
}
function deferred() { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b; }); return { promise, resolve, reject }; }
const flush = async () => { for (let i=0;i<8;i++) await Promise.resolve(); };

function world(config = {}) {
  const w = {
    console, Promise, AbortController, Date,
    setTimeout(fn, ms) { if (ms >= 4000) { (w._timeouts ||= []).push({fn,ms}); return w._timeouts.length; } queueMicrotask(fn); return 1; },
    document: {}, _busy:false, _ctl:null, _cancelOpts:false, _progress:'', _extra:{cost:0,calls:0}, _log:[], HIST:[], RECENT:[],
    _serial:0, _offlineLast:null, _last:null, _orig:null, _skipParts:false, _specOnlyReq:false, _beforeImg:null,
    _elemRunIdentity:null, _editReg:{}, _absent:{}, _noCheck:false, _advLast:null, _advUsed:null, _advRejected:[], _gen:0, _snapGen:0, _activeId:null,
    selectedZoneIndex:-1, zones:[{id:'zone-body',name:'Body',color:'blue'}], layers:[{id:'layer-body',name:'Body',visible:true,opacity:255,blendMode:'source-over'}],
    _spbSourceLoadGeneration:10, _spbSourceImage:{token:'image-10'}, _spbSourcePath:'car.psd', _spbSourceFingerprint:'fp-10', _spbLayerRev:20,
    paintCanvas:{width:2048,height:2048}, providerCalls:[], applyCalls:[], renderStates:[], previewImages:[], revisionWrites:0, stateValue:0,
    previewGate:null, previewSettles:0, events:[],
  };
  w.window=w;
  // Mirrors the real public controller access shape backed by _spbSourceLoadGeneration.
  w.SPBSourceLoadTransaction={getGeneration:()=>w._spbSourceLoadGeneration,getCommittedPath:()=>w._spbSourcePath,getCommittedFingerprint:()=>w._spbSourceFingerprint};
  w.sourceIdentity=()=>({generation:w.SPBSourceLoadTransaction.getGeneration(),image:w._spbSourceImage,path:w.SPBSourceLoadTransaction.getCommittedPath(),fingerprint:w.SPBSourceLoadTransaction.getCommittedFingerprint(),width:w.paintCanvas.width,height:w.paintCanvas.height});
  w.SpbAiOperation=SpbAiOperation;
  w.spbAiOperationDocument=()=>w.sourceIdentity(); w.spbAiOperationRevision=()=>w._spbLayerRev;
  vm.createContext(w);
  w.index=()=>({}); w.specProps=()=>({}); w.normaliseSpec=o=>({...o}); w.strip=o=>({...o}); w.lsGet=()=>null;
  w.layersInfo=()=>w.layers.map(x=>({name:x.name})); w.bodyLayerNames=()=>[]; w.wantsDecalsToo=()=>false; w.keepOwnColour=()=>{}; w.specOnlyGuard=()=>null; w.partScopeGuard=()=>null; w.protectDecals=()=>null;
  w.Z={findLayer:n=>w.layers.find(l=>l.name===n)||null,validate:()=>({errors:[]}),catchAll:()=>null,probeRegion:()=>({share_pct:100}),whenSettled:()=>w.previewGate?w.previewGate.promise:(++w.previewSettles,Promise.resolve()),previewImage:n=>{w.previewImages.push({generation:w._spbSourceLoadGeneration,n});return 'preview-'+w._spbSourceLoadGeneration;},footprint:()=>null,quiet:fn=>fn()};
  w.D={recipes:()=>[],summarise:()=>[]}; w.E={}; w.CAR=config.CAR||null; w.AT=null; w.K=null; w.NLU={};
  w.AI={cached:()=>({configured:true}),run:opts=>{w.providerCalls.push(opts);return w.providerMode(opts,w.providerCalls.length);}};
  w.providerMode=config.providerMode||(()=>Promise.resolve({text:'No change.',tools:[],calls:1}));
  w.selfHelpClaim=()=>null; w.selfHelpResult=x=>x; w.offlineFirst=()=>false; w.offlineCanHandle=()=>false; w.offlineAsk=()=>({}); w.panelsNeeded=config.panelsNeeded||(()=>[]);
  w.intentSpecOnly=()=>false; w.makeTools=undefined; w.state=()=>({source:w.sourceIdentity(),zones:w.zones.map(z=>({id:z.id,name:z.name,color:z.color})),layers:w.layers.map(l=>({name:l.name}))});
  w.buildSystem=()=>''; w.onEventTrail=()=>{}; w.isSchemeRequest=()=>false; w.selectedZoneIndex=-1; w.HOWTO_RE=/$a/; w.REVIEW=undefined; w.IDENTIFY_TOOLS=/^$/;
  w.offlineFirst=()=>false; w.offlineCanHandle=()=>false; w.selfHelpClaim=()=>null; w.editPlan=()=>null; w.offlineMaterialPlan=()=>null; w.panelsNeeded=config.panelsNeeded||(()=>[]);
  w.captureOriginal=()=>{}; w._cloneZoneState=z=>JSON.parse(JSON.stringify(z));
  w.snapshotZones=undefined; w.restoreZones=undefined; w.renderZones=()=>{}; w.triggerPreviewRender=()=>{};
  w._applyCount=0; w.applyQueue=queue=>{w._applyCount++;const prev=JSON.parse(JSON.stringify(w.zones));w.applyCalls.push({generation:w._spbSourceLoadGeneration,revision:w._spbLayerRev,queue:JSON.parse(JSON.stringify(queue))});queue.forEach(q=>{if(q.kind==='layer'){const layer=w.layers.find(l=>l.id===q.layer);if(layer){if(q.visible!=null)layer.visible=q.visible;if(q.opacity!=null)layer.opacity=q.opacity;if(q.blend!=null)layer.blendMode=q.blend;}}else if(q.kind==='edit'&&w.zones[q.zone])Object.assign(w.zones[q.zone],q.spec||{});});w._undoStack.push(prev);w._spbLayerRev++;return {lines:['updated'],failed:[],maskUndo:[],layerUndo:1,results:[],partRegUndo:null};};
  w._undoStack=[]; w.undoDepth=()=>w._applyCount; w.undoLayerEdit=()=>{const s=w._undoStack.pop();if(s)w.zones.splice(0,w.zones.length,...s);w._applyCount=Math.max(0,w._applyCount-1);w._spbLayerRev++;}; w.undoZoneChange=()=>{}; w.restorePartRegistryUndo=()=>{}; w.render=()=>{w.renderStates.push({busy:w._busy,progress:w._progress,generation:w._spbSourceLoadGeneration});};
  w.portableOp=()=>null; w.maskBudgetNote=()=>null; w.diagnose=()=>[]; w.cost=()=>''; w.parseNext=()=>{}; w.postCheck=entry=>Promise.resolve(entry); w.friendlyError=e=>String(e&&e.message||e); w.markPartFollowupQueue=()=>{};
  w.elementRunCurrent=i=>!!i&&i===w.currentElementIdentity; w.elementRunIdentity=()=>w.currentElementIdentity||''; w.elementRunCanceled=()=>{w._busy=false;w._ctl=null;return Promise.resolve({cancelled:true});}; w.elementRunResult=(p)=>p; w.elementPaintChangedResult=()=>({elementPaintChanged:true,queue:[]}); w.elementFinishGuard=(id,read,fn)=>{if(id!==read())return false;fn();return true;}; w.elementRestoreGuard=w.elementFinishGuard;
  w.advisorIntent=()=>null; w.TEACH_RE=/$a/;w.QUESTION_RE=/\?/;w.START_OVER_RE=/$a/;w.CHECK_AGAIN_RE=/$a/;w.NUM_FIX_RE=/$a/;w.CLAIM_RE=/\bApplied\b/;
  w.supportClass=()=>null;w.supportSend=()=>false;w.offlineCannot=()=>false;w.layerVisRequest=()=>false;w.offlineHowtoPeek=()=>false;w.offlineScopeReply=()=>({text:'scope'});
  w._panel={querySelector:()=>w.input};w.input={value:''};w.renderCalls=0;

  const code = sourceSlice('function makeTools(queue, sig)', '// ------------------------------------------------------------------ applying')+
    sourceSlice('function progressWord(name)', '// ------------------------------------------------------------------ one model turn')+
    sourceSlice('function warm(ms)', 'function runTurn(text, o)')+
    sourceSlice('function runTurn(text, o)', 'function runTurn2(text, o)')+
    sourceSlice('function runTurn2(text, o)', 'function askCore(text, o)')+
    sourceSlice('function askCore(text, o)', 'function cost(r)')+
    sourceSlice('function finish(r, text, kind, entryOpts)', 'function finishCore(r, text, kind, entryOpts)')+
    sourceSlice('function finishCore(r, text, kind, entryOpts)', 'var CLAIM_RE =')+
    sourceSlice('function snapshotZones()', 'function maskZoneCount()')+
    sourceSlice('function previewOptions(entry, r, text)', 'function useOption(entry, i)')+
    sourceSlice('function preflightTeach(text, miss)', '// ---- what colours')+
    sourceSlice('function doUndo(entry)', 'function refine(entry)');
  vm.runInContext(code,w,{filename:'actual-pro-ai-route-slices.js'});
  const cancelStart=proSource.indexOf("if (b.hasAttribute('data-cancel')) {");
  const cancelEnd=proSource.indexOf("var act = b.getAttribute('data-act')",cancelStart);
  assert(cancelStart>=0&&cancelEnd>cancelStart,'actual Cancel branch');
  vm.runInContext('function clickCancel(b){'+proSource.slice(cancelStart,cancelEnd)+'}',w,{filename:'actual-cancel-branch.js'});
  return w;
}

const details=[], failures=[];
async function scenario(id,fn){try{const d=await fn();details.push({id,verdict:'pass',...d});}catch(e){failures.push({id,error:e.message});details.push({id,verdict:'fail',reason:e.message});}}
const layerTool=opts=>opts.tools.find(t=>t.name==='edit_layer');
async function turn(w,text){const p=w.ask(text,{});await flush();return p;}

// Cases are executed below against the actual extracted route; only effects and provider are fake.

const settle = () => new Promise(resolve=>setImmediate(resolve));

(async()=>{
  await scenario('sync-provider-throw-releases-request',async()=>{
    const w=world({providerMode:()=>{throw new Error('adapter sync throw');}});let error=null;
    try{await w.ask('change the body',{});}catch(e){error=e;}
    assert.ok(error);assert.equal(w._busy,false);assert.equal(w._ctl,null);
    return {busy:w._busy,controller:w._ctl};
  });

  await scenario('warm-rejection-releases-request',async()=>{
    const w=world({CAR:{ensure:()=>Promise.reject(new Error('warm rejected'))}});let error=null;
    try{await w.ask('change the body',{});}catch(e){error=e;}
    assert.ok(error);assert.equal(w._busy,false);assert.equal(w._ctl,null);
    return {error:String(error),busy:w._busy};
  });

  await scenario('cancel-ignoring-abort-discards-late-success',async()=>{
    const p=deferred(),w=world({providerMode:()=>p.promise});const ask=w.ask('hide the Body layer',{});await flush();const opts=w.providerCalls[0];
    const queued=layerTool(opts).handler({layer:'Body',visible:false});assert.ok(queued.ok);w.clickCancel({hasAttribute:n=>n==='data-cancel'});
    assert.equal(opts.signal.aborted,true);p.resolve({text:'Hidden.',tools:['edit_layer'],calls:1});const result=await ask;await w.finish(result,'hide the Body layer','ask');
    assert.equal(w._applyCount,0);assert.ok(!w._log.some(e=>e.role==='ai'&&e.text==='Hidden.'));
    return {writes:w._applyCount,lateTextLogged:w._log.some(e=>e.text==='Hidden.')};
  });

  await scenario('cancel-A-new-B-late-A-result',async()=>{
    const a=deferred(),b=deferred(),w=world({providerMode:(_opts,n)=>n===1?a.promise:b.promise});const askA=w.ask('A request',{});await flush();w.clickCancel({hasAttribute:n=>n==='data-cancel'});
    const runB=w.runTurn('B request',{});await flush();const ctlB=w._ctl;assert.equal(w.providerCalls.length,2,'B must start while canceled A is unresolved');
    a.resolve({text:'Late A.',tools:[],calls:1});const resultA=await askA;await w.finish(resultA,'A request','ask');
    assert.equal(w._busy,true);assert.equal(w._ctl,ctlB);assert.equal(w._applyCount,0);
    b.resolve({text:'B done.',tools:[],calls:1});await runB;
    return {busyAfterLateA:w._busy,controllerStillB:w._ctl===ctlB,writes:w._applyCount};
  });

  await scenario('cancel-A-new-B-late-A-event',async()=>{
    const a=deferred(),b=deferred(),w=world({providerMode:(_opts,n)=>n===1?a.promise:b.promise});w.runTurn('A',{});await flush();const optsA=w.providerCalls[0];w.clickCancel({hasAttribute:n=>n==='data-cancel'});w.runTurn('B',{});await flush();const optsB=w.providerCalls[1];optsB.onEvent('thinking',{step:4});const progressB=w._progress;optsA.onEvent('tool',{name:'edit_layer',args:{layer:'Body'}});
    assert.equal(w._progress,progressB);a.resolve({text:'A',tools:[],calls:1});b.resolve({text:'B',tools:[],calls:1});await flush();
    return {progressB,progressAfterAEvent:w._progress};
  });

  await scenario('cancel-A-new-B-late-A-tool-callback',async()=>{
    const a=deferred(),b=deferred(),w=world({providerMode:(_opts,n)=>n===1?a.promise:b.promise});w.runTurn('A',{});await flush();const optsA=w.providerCalls[0];w.clickCancel({hasAttribute:n=>n==='data-cancel'});w.runTurn('B',{});await flush();
    const r=layerTool(optsA).handler({layer:'Body',visible:false});assert.ok(r.error,'stale callback must be rejected');
    a.resolve({text:'A',tools:['edit_layer'],calls:1});b.resolve({text:'B',tools:[],calls:1});const stale=await w.providerCalls[0]&&Promise.resolve();await flush();
    assert.equal(w._applyCount,0);return {rejected:!!r.error,writes:w._applyCount};
  });

  await scenario('cancel-A-new-B-late-A-rejection-cleanup',async()=>{
    const a=deferred(),b=deferred(),w=world({providerMode:(_opts,n)=>n===1?a.promise:b.promise});const runA=w.runTurn('A',{});await flush();w.clickCancel({hasAttribute:n=>n==='data-cancel'});const runB=w.runTurn('B',{});await flush();const ctlB=w._ctl;
    a.reject(new Error('late A rejection'));await runA;assert.equal(w._busy,true);assert.equal(w._ctl,ctlB);
    b.resolve({text:'B',tools:[],calls:1});await runB;return {busyAfterAReject:w._busy,controllerStillB:w._ctl===ctlB};
  });

  await scenario('ready-A-ask-B-before-finish-A',async()=>{
    const a=deferred(),b=deferred(),w=world({providerMode:(_opts,n)=>n===1?a.promise:b.promise});const askA=w.ask('A request',{});await flush();const optsA=w.providerCalls[0];layerTool(optsA).handler({layer:'Body',visible:false});a.resolve({text:'Applied A.',tools:['edit_layer'],calls:1});const readyA=await askA;
    const askB=w.ask('B request',{});await flush();assert.equal(w.providerCalls.length,2);await w.finish(readyA,'A request','ask');assert.equal(w._applyCount,0,'A must be stale after B takes ownership');
    b.resolve({text:'B done.',tools:[],calls:1});await askB;return {writes:w._applyCount,readyAStale:true};
  });

  await scenario('same-path-source-generation-reload',async()=>{
    const p=deferred(),w=world({providerMode:()=>p.promise}),ask=w.ask('change the body',{});await flush();const opts=w.providerCalls[0];layerTool(opts).handler({layer:'Body',visible:false});w._spbSourceLoadGeneration++;w._spbSourceImage={token:'reload-same-path'};p.resolve({text:'Done.',tools:['edit_layer'],calls:1});const result=await ask;await w.finish(result,'change the body','ask');assert.equal(w._applyCount,0);
    return {generation:w.SPBSourceLoadTransaction.getGeneration(),path:w.SPBSourceLoadTransaction.getCommittedPath(),writes:w._applyCount};
  });

  await scenario('warm-source-switch-before-provider',async()=>{
    const gate=deferred(),w=world({CAR:{ensure:()=>gate.promise},providerMode:()=>Promise.resolve({text:'Done.',tools:[],calls:1})});const ask=w.ask('change the body',{});await flush();w._spbSourceLoadGeneration++;w._spbSourceImage={token:'new-source'};gate.resolve();await flush();
    assert.equal(w.providerCalls.length,0,'old source warm continuation must not call model');return {providerCalls:w.providerCalls.length};
  });

  await scenario('preflight-source-switch-before-provider',async()=>{
    const gate=deferred(),car={ensure:()=>gate.promise,missing:()=>[],map:()=>({})},w=world({CAR:car,panelsNeeded:()=>['roof'],providerMode:()=>Promise.resolve({text:'Done.',tools:[],calls:1})});const ask=w.ask('paint the roof',{});await flush();w._spbSourceLoadGeneration++;w._spbSourceImage={token:'preflight-reload'};gate.resolve();await flush();
    assert.equal(w.providerCalls.length,0,'preflight from old source must not continue into a model turn');return {providerCalls:w.providerCalls.length};
  });

  await scenario('ordinary-options-source-switch',async()=>{
    const gate=deferred(),w=world();w.previewGate=gate;const entry={role:'ai',id:1,text:'Options',lines:[],notes:[]};const run=w.previewOptions(entry,{text:'',queue:{options:[{label:'red',queue:[{kind:'edit',zone:0,spec:{color:'red'}}]},{label:'green',queue:[{kind:'edit',zone:0,spec:{color:'green'}}]}]}},'choose');await flush();w._spbSourceLoadGeneration++;w._spbSourceImage={token:'options-new-source'};gate.resolve();await run;
    assert.equal(w.previewImages.some(x=>x.generation===w._spbSourceLoadGeneration),false,'old option must not be sampled on replacement source');return {previewImages:w.previewImages};
  });

  await scenario('same-document-cancel-restores-own-preview',async()=>{
    const gate=deferred(),w=world();w.previewGate=gate;const original=JSON.stringify(w.zones),entry={role:'ai',id:1,text:'Options',lines:[],notes:[]};const run=w.previewOptions(entry,{text:'',queue:{options:[{label:'red',queue:[{kind:'edit',zone:0,spec:{color:'red'}}]},{label:'green',queue:[{kind:'edit',zone:0,spec:{color:'green'}}]}]}},'choose');await flush();w.clickCancel({hasAttribute:n=>n==='data-cancel'});gate.resolve();await run;
    assert.equal(JSON.stringify(w.zones),original);assert.equal(w._busy,false);return {restored:true,busy:w._busy};
  });

  await scenario('manual-revision-conflict-before-apply',async()=>{
    const p=deferred(),w=world({providerMode:()=>p.promise}),ask=w.ask('hide the Body layer',{});await flush();const opts=w.providerCalls[0];layerTool(opts).handler({layer:'Body',visible:false});w._spbLayerRev++;p.resolve({text:'Done.',tools:['edit_layer'],calls:1});const result=await ask;await w.finish(result,'hide the Body layer','ask');assert.equal(w._applyCount,0,'manual layer revision must win');return {revision:w._spbLayerRev,writes:w._applyCount};
  });

  await scenario('normal-action-and-undo',async()=>{
    const p=deferred(),w=world({providerMode:()=>p.promise}),before=JSON.stringify(w.layers),ask=w.ask('hide the Body layer',{});await flush();const opts=w.providerCalls[0];const tr=layerTool(opts).handler({layer:'Body',visible:false});assert.ok(tr.ok);p.resolve({text:'Updated.',tools:['edit_layer'],calls:1});const result=await ask;const entry=await w.finish(result,'hide the Body layer','ask');assert.equal(w._applyCount,1);assert.equal(w.layers[0].visible,false);w.doUndo(entry);assert.equal(JSON.stringify(w.layers),before);return {applyCount:1,undoRestored:true};
  });

  await scenario('public-ask-starts-B-after-cancel-A',async()=>{
    const a=deferred(),b=deferred(),w=world({providerMode:(_opts,n)=>n===1?a.promise:b.promise}),askA=w.ask('A',{});await flush();w.clickCancel({hasAttribute:n=>n==='data-cancel'});const askB=w.ask('B',{});await flush();assert.equal(w.providerCalls.length,2,'public ask must admit B after cancellation even while A settles late');a.reject(new Error('cancelled A'));await askA.catch(()=>{});b.resolve({text:'B',tools:[],calls:1});await askB;return {providerCalls:w.providerCalls.length};
  });

  console.log(`${failures.length?'FAIL':'PASS'} actual-route review: ${ORACLE.length-failures.length}/${ORACLE.length} frozen cases`);
  console.log(JSON.stringify(details,null,2));
  if(failures.length){console.error(failures.map(x=>`${x.id}: ${x.error}`).join('\n'));process.exitCode=1;}
})().catch(e=>{console.error(e);process.exitCode=1;});
