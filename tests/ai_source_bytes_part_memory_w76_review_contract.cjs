'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = process.cwd();
const pins = {
  canvas: '_easy_claude_work/ai14h_w76_review/frozen/paint-booth-3-canvas.js',
  pro: '_easy_claude_work/ai14h_w76_review/frozen/spb-pro-ai.js',
  bridge: '_easy_claude_work/ai14h_w76_review/frozen/spb-ai-part-memory-project.js',
  lease: '_easy_claude_work/ai14h_w76_review/frozen/spb-ai-lease.js',
  memory: '_easy_claude_work/ai14h_w76_review/frozen/spb-ai-part-memory.js',
  oracle: '_easy_claude_work/ai14h_w76_review_fresh_oracle.json'
};
const hashes = Object.fromEntries(Object.entries(pins).map(([k,p]) => [k,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex').toUpperCase()]));
assert.equal(hashes.canvas,'1BD43BAF7D1BDAC1E07417D6FF6B30F71E78F1FF9169987C03198DD63DC2D4DA');
assert.equal(hashes.pro,'9709D6A2EC1A72376D07E9A8E07D2252C95888B2E365540F2AD0C6EFD73E3BD1');
assert.equal(hashes.bridge,'763D36ADDCA501256E1346D58B797D339B15666D04273CBF5C4840B15C1C6FC1');
assert.equal(hashes.lease,'DE276372A763310EC051DB141FCB1D601E11DBF193843E2B21A405226F782134');
assert.equal(hashes.memory,'6E0D1E1466FECA847D3A1C3300F32779BA610F3B6C72C7904A6C8FD97A6B3652');
const ORACLE = JSON.parse(fs.readFileSync(path.join(root,pins.oracle),'utf8'));
const oracleSha = crypto.createHash('sha256').update(fs.readFileSync(path.join(root,pins.oracle))).digest('hex').toUpperCase();
assert.equal(oracleSha,'C0F06D9E7AF26C38ECA1CFDC610F2DA2EBAB72B69DB7B152DB1BF007F03FE136');
const outcomes=[]; const findings=[];
function pass(id,details={}) { outcomes.push({id,result:'PASS',...details}); }
function extractFunction(source, signature) {
  const start=source.indexOf(signature); assert(start>=0,`missing ${signature}`);
  const brace=source.indexOf('{',start); let depth=0,q=null,esc=false,line=false,block=false;
  for(let i=brace;i<source.length;i++) { const c=source[i],n=source[i+1];
    if(line){if(c==='\n')line=false;continue;} if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}
    if(q){if(esc)esc=false;else if(c==='\\')esc=true;else if(c===q)q=null;continue;}
    if(c==='/'&&n==='/'){line=true;i++;continue;} if(c==='/'&&n==='*'){block=true;i++;continue;}
    if(c==='"'||c==="'"||c==='`'){q=c;continue;} if(c==='{')depth++; else if(c==='}'&&--depth===0)return source.slice(start,i+1);
  } throw new Error('unterminated '+signature);
}
const canvas=fs.readFileSync(path.join(root,pins.canvas),'utf8');
const pro=fs.readFileSync(path.join(root,pins.pro),'utf8');
const begin=extractFunction(canvas,'function _spbBeginSourceLoad(');
const current=extractFunction(canvas,'function _spbIsCurrentSourceLoad(');
const result=extractFunction(canvas,'function _spbSourceLoadResult(');
const fpBytes=extractFunction(canvas,'async function _spbFingerprintBytes(');
const fpText=extractFunction(canvas,'async function _spbFingerprintText(');
const layeredFp=extractFunction(canvas,'function _spbLayeredSourceFingerprint(');
function extractObjectAssignment(source, signature) { const start=source.indexOf(signature); assert(start>=0); const brace=source.indexOf('{',start); let depth=0,q=null,esc=false,line=false,block=false; for(let i=brace;i<source.length;i++){const c=source[i],n=source[i+1];if(line){if(c==='\n')line=false;continue;}if(block){if(c==='*'&&n==='/'){block=false;i++;}continue;}if(q){if(esc)esc=false;else if(c==='\\')esc=true;else if(c===q)q=null;continue;}if(c==='/'&&n==='/'){line=true;i++;continue;}if(c==='/'&&n==='*'){block=true;i++;continue;}if(c==='\"'||c==="'"||c==='`'){q=c;continue;}if(c==='{')depth++;else if(c==='}'&&--depth===0)return source.slice(start,i+1);}throw new Error('unterminated '+signature); } const txBlock=extractObjectAssignment(canvas,'window.SPBSourceLoadTransaction = {');
assert(txBlock.includes('SPBSourceLoadTransaction = {')); 
const canvasRuntime=vm.createContext({Uint8Array,TextEncoder,Math,Number,String,Object,Array,Error,crypto:crypto.webcrypto,console:{error(){}}});
vm.runInContext(`var window=this; var _spbSourceLoadGeneration=0,_spbCommittedSourcePath='',_spbCommittedSourceFingerprint='',_spbCommittedSourceGeneration=0,_spbSourceLoadPending=false,_spbCommittedSourceKind='file',_psdPath='';\n${begin}\n${current}\n${result}\n${fpBytes}\n${fpText}\n${layeredFp}\n${txBlock}\nthis.seed=function(path,fp,kind){var t=window.SPBSourceLoadTransaction.begin(path,kind);_spbCommittedSourcePath=path;_spbCommittedSourceFingerprint=fp;return window.SPBSourceLoadTransaction.result(t,true,{committedPath:path,fingerprint:fp,sourceKind:kind});}; this.layerFp=_spbLayeredSourceFingerprint;this.fpText=_spbFingerprintText;this.state=function(){return {path:window.SPBSourceLoadTransaction.getCommittedPath(),fp:window.SPBSourceLoadTransaction.getCommittedFingerprint(),kind:window.SPBSourceLoadTransaction.getCommittedKind(),gen:window.SPBSourceLoadTransaction.getGeneration(),committed:window.SPBSourceLoadTransaction.isCommitted(),loading:window.SPBSourceLoadTransaction.isLoading()};};`,canvasRuntime);
const shaA='a'.repeat(64),shaB='b'.repeat(64),composite='c'.repeat(64);
assert.equal(canvasRuntime.layerFp({sourceBytesSha256:shaA},composite),`file-sha256:${shaA}`);
assert.notEqual(canvasRuntime.layerFp({sourceBytesSha256:shaA},composite),canvasRuntime.layerFp({sourceBytesSha256:shaB},composite));
assert.equal(canvasRuntime.layerFp({},composite),`composite-sha256:${composite}`);
assert.equal(canvasRuntime.layerFp({},'fnv1a32-1234abcd-22'),'composite-fnv1a32:fnv1a32-1234abcd-22');
for(const bad of ['',null,'A'.repeat(64),'a'.repeat(63),'g'.repeat(64)]) assert.throws(()=>canvasRuntime.layerFp({sourceBytesSha256:bad},composite),/invalid source byte fingerprint/);
pass('digest-prefix-validation', {validStrong:true, weakCompositeTagged:true, malformedValuesRejected:5});
const fnvRuntime=vm.createContext({Uint8Array,Math,Number,String,Object,Array,Error});
vm.runInContext(`${fpBytes}\n${fpText}\nthis.hash=_spbFingerprintText;`,fnvRuntime);
(async()=>{
  const fnv=await fnvRuntime.hash('abc'); assert.match(fnv,/^fnv1a32-[0-9a-f]{8}-3$/);
  assert.equal(await canvasRuntime.fpText('abc'),crypto.createHash('sha256').update('abc').digest('hex'));
  pass('strong-and-no-webcrypto-fallback',{sha256:'webcrypto SHA-256 confirmed',fallback:fnv});

  // Exercise the actual transactional helper closures and object with a retained old document.
  canvasRuntime.seed('C:/car.psd',`file-sha256:${shaA}`,'layered');
  const before=canvasRuntime.state(); assert.equal(before.committed,true);
  const doPsd=extractFunction(canvas,'async function _doPSDImport(');
  const importCtx=vm.createContext({console:{error(){}},Math,Number,String,Object,Array,Error,Promise,fetch:async()=>({ok:true,status:200,json:async()=>({success:true,sourceBytesSha256:'not-a-lowercase-sha256'})})});
  vm.runInContext(`var window=this; window._spbPsdImportCount=0; window._spbPsdImportInFlight=false; window.SPBRenderReadiness={refresh:function(){}}; window.SPBPSDImportSafety={flattenLayerTree:function(){throw Error('must not stage');}}; window.SPBDocumentCapability={chooseInitialLayer:function(){throw Error('must not stage');}}; var _spbCommittedSourcePath='C:/car.psd',_spbCommittedSourceFingerprint='file-sha256:${shaA}',_spbCommittedSourceGeneration=1,_spbSourceLoadGeneration=1,_spbSourceLoadPending=false,_spbCommittedSourceKind='layered',_psdPath='C:/car.psd'; `,importCtx);
  // Install actual transaction functions/closure block and the actual candidate digest helper.
  vm.runInContext(`${begin}\n${current}\n${result}\n${layeredFp}\n${txBlock}\n${doPsd}\nvar flattenCalls=0; window.SPBPSDImportSafety.flattenLayerTree=function(){flattenCalls++;}; this.run=function(){return _doPSDImport('C:/replacement.psd');}; this.state=function(){return window.SPBSourceLoadTransaction?{path:window.SPBSourceLoadTransaction.getCommittedPath(),fp:window.SPBSourceLoadTransaction.getCommittedFingerprint(),kind:window.SPBSourceLoadTransaction.getCommittedKind(),committed:window.SPBSourceLoadTransaction.isCommitted(),pending:window.SPBSourceLoadTransaction.isLoading(),count:window._spbPsdImportCount,flattenCalls:flattenCalls}:null;};`,importCtx);
  // Use the actual earlier source transaction seed helper by directly publishing the prior committed tuple.
  importCtx._spbCommittedSourcePath='C:/car.psd'; importCtx._spbCommittedSourceFingerprint=`file-sha256:${shaA}`; importCtx._spbCommittedSourceGeneration=1; importCtx._spbSourceLoadGeneration=1;
  const beforeBad=importCtx.state();
  const badResult=await importCtx.run(); const afterBad=importCtx.state();
  assert.equal(badResult.ok,false); assert.match(badResult.error,/invalid source byte fingerprint/);
  assert.equal(afterBad.path,beforeBad.path); assert.equal(afterBad.fp,beforeBad.fp); assert.equal(afterBad.kind,'layered');
  assert.equal(afterBad.pending,false); assert.equal(afterBad.count,0); assert.equal(afterBad.flattenCalls,0); assert.equal(afterBad.committed,true);
  pass('malformed-digest-precommit-retains-prior-document',{error:badResult.error,oldCommittedSourceRetained:true,stagingOrMutationReached:false,settled:true});

  // Actual candidate controller functions: scoped source, durable gate, init hook, pending-aware queue.
  const scoped=extractFunction(pro,'function scopedPartSourceNow(');
  const gate=extractFunction(pro,'function durablePartMemorySourceIdentityCurrent(');
  const ensure=extractFunction(pro,'function ensurePartMemoryRuntime(');
  const hashMask=extractFunction(pro,'function partMemoryHash(');
  const ownerCountFn=extractFunction(pro,'function partMemoryOwnerCount(');
  const partRegion=extractFunction(pro,'function partRegionKey(');
  const editKey=extractFunction(pro,'function editKey(');
  const prior=extractFunction(pro,'function hasPriorPartIdentity(');
  const queue=extractFunction(pro,'function queueEditZones(');
  const bridgeSrc=fs.readFileSync(path.join(root,pins.bridge),'utf8');
  const memorySrc=fs.readFileSync(path.join(root,pins.memory),'utf8');
  const proCtx=vm.createContext({console:{},Object,String,RegExp,JSON,Array,Number,Math,Error,Uint8Array,Date,window:{SPBSourceLoadTransaction:canvasRuntime.window.SPBSourceLoadTransaction},document:{getElementById:()=>({width:2048,height:2048})}});
  vm.runInContext(memorySrc,proCtx); vm.runInContext(bridgeSrc,proCtx);
  vm.runInContext(`var _partMemoryRuntime=null,zones=[],CAR={},_psdPath='C:/car.psd',currentPath='C:/car.psd'; function getCurrentSourcePaintFile(){return currentPath;}\n${scoped}\n${gate}\n${hashMask}\n${partRegion}\n${editKey}\n${ownerCountFn}\nfunction partMemorySource(s){return s;} function partMemoryRich(){return null;} function partOwnerCurrent(){return false;} function scopedPartLayersNow(){return null;} function carSig(){return 'car';}\n${ensure}\nthis.ensure=ensurePartMemoryRuntime;this.scoped=scopedPartSourceNow;`,proCtx);
  canvasRuntime.seed('C:/car.psd',`composite-sha256:${composite}`,'layered');
  proCtx.window.SPBSourceLoadTransaction=canvasRuntime.window.SPBSourceLoadTransaction;
  const weakNow=proCtx.scoped(); assert.ok(weakNow&&weakNow.fingerprint===`composite-sha256:${composite}`,'weak layered document still has a usable committed session source');
  const mem=proCtx.window.SpbAIPartMemory, origSave=mem.saveRecord; let capturedSources=[];
  proCtx.window.SpbAIPartMemory=Object.assign({},mem,{saveRecord:function(zone,source,proof){capturedSources.push(source);return origSave(zone,source,proof);}});
  const runtime=proCtx.ensure(); assert.ok(runtime&&typeof runtime.capture==='function');
  runtime.capture({}); assert.equal(capturedSources.length,1); assert.equal(capturedSources[0],null,'weak layered session cannot be passed to durable capture');
  canvasRuntime.seed('C:/car.psd',`file-sha256:${shaA}`,'layered');
  runtime.capture({}); assert.equal(capturedSources.length,2); assert.equal(capturedSources[1].fingerprint,`file-sha256:${shaA}`,'strong exact current digest reaches actual memory module');
  const pendingTx=canvasRuntime.window.SPBSourceLoadTransaction.begin('C:/replacement.psd','layered');
  runtime.capture({}); assert.equal(capturedSources.length,3); assert.equal(capturedSources[2],null,'pending replacement cannot persist/rebind old source');
  canvasRuntime.window.SPBSourceLoadTransaction.result(pendingTx,false,{error:'fixture failure'});
  runtime.capture({}); assert.equal(capturedSources.length,4); assert.equal(capturedSources[3].path,'C:/car.psd'); assert.equal(capturedSources[3].fingerprint,`file-sha256:${shaA}`,'failed replacement retains prior committed document A at its settled generation');
  pass('weak-layered-session-remains-usable-but-durable-rebind-requires-current-file-digest',{weakSessionUsable:true,weakDurable:false,strongCaptureSource:`file-sha256:${shaA}`,pendingReplacementCapture:false,failedReplacementKeepsA:true});

  // queueEditZones actual pending provenance block and unrelated selector behavior.
  const queueFnCode=`${partRegion}\n${editKey}\n${prior}\n${queue}\n`;
  function runQueue(pendingRegion,requestRegion={part:'roof'}){
    const regionJson=JSON.stringify(JSON.stringify(pendingRegion));
    const q=vm.createContext({Object,String,RegExp,JSON,Array,Number,Math,Error});
    vm.runInContext(`${queueFnCode}\nvar zones=[{id:'saved-roof',name:'Saved roof',muted:false,useRegion:true,regionMask:new Uint8Array([1]),_spbAIPartMemoryPending:{provenance:{r:${regionJson}}}}];var _editReg={},_editRegSig='car',_editRegPendingBefore={};var CAR={};var window={};var adds=[];function carSig(){return 'car';}function scopedPartProofAt(){return null;}function scopedPartProofMatches(){return false;}function friendlyZoneError(e){return String(e);}function editPlural(){return false;}function add(spec){adds.push(spec);return {region_check:{share_pct:40}};}function edit(){return {};};this.run=function(){return queueEditZones({zones:[{name:'Requested roof',region:${JSON.stringify(requestRegion)},color:'source',_meta:{label:'roof',kind:'colour'}}]},add,edit,{});};this.out=function(){return {adds:adds,zone:zones[0]};};`,q);
    const result=q.run(); return {result, state:q.out()};
  }
  const roof=runQueue({part:'roof'}); assert.equal(roof.state.adds.length,0); assert.equal(roof.result.errs.length,1); assert.match(roof.result.errs[0],/cannot safely keep the existing part colour/); assert.ok(roof.state.zone._spbAIPartMemoryPending);
  const hood=runQueue({part:'hood'}); assert.equal(hood.state.adds.length,1); assert.equal(hood.result.errs.length,0); assert.ok(hood.state.zone._spbAIPartMemoryPending);
  const broadRoofOverSavedPortion=runQueue({part:'roof',portion:'upper'},{part:'roof'});
  const narrowRoofOverSavedWhole=runQueue({part:'roof'},{part:'roof',portion:'upper'});
  if (broadRoofOverSavedPortion.state.adds.length !== 0 || narrowRoofOverSavedWhole.state.adds.length !== 0) findings.push({severity:'P1 safety gap',case:'overlapping named-part region scopes differ by portion',observed:{savedUpperRequestWhole:broadRoofOverSavedPortion.state.adds.length,savedWholeRequestUpper:narrowRoofOverSavedWhole.state.adds.length},queueSpecs:[broadRoofOverSavedPortion.state.adds[0],narrowRoofOverSavedWhole.state.adds[0]].filter(Boolean),reason:'The saved and requested scopes are overlapping (whole roof contains upper roof), but different editKey values make the pending owner guard miss both directions; a source-color zone can be added above and repaint original-source pixels over the saved part.'});
  pass('pending-same-part-blocks-source-repaint-but-unrelated-part-does-not',{samePartQueued:0,samePartClarification:roof.result.errs[0],unrelatedPartQueued:hood.state.adds.length,pendingRecordUnchanged:true,overlappingSelectorVariationsQueued:{savedUpperRequestWhole:broadRoofOverSavedPortion.state.adds.length,savedWholeRequestUpper:narrowRoofOverSavedWhole.state.adds.length}});

  // W36 current-generation lease behavior, executed from the exact current isolated adapter bytes.
  const leaseSrc=fs.readFileSync(path.join(root,pins.lease),'utf8');
  const leaseCtx=vm.createContext({Date,window:{}}); vm.runInContext(leaseSrc,leaseCtx);
  const L=leaseCtx.window.SpbAiLease; assert.equal(L.begin('external'),true); const gA=L.generation(); assert.equal(L.end(gA),true); assert.equal(L.begin('external'),true); const gB=L.generation(); assert.ok(gB>gA); assert.equal(L.end(gA),false); assert.equal(L.generation(),gB); assert.equal(L.end(gB),true);
  pass('current-w36-lease-stale-generation-cannot-release-successor',{adapterSha256:hashes.lease,staleEnd:false,generationBAfterStale:true});

  console.log(JSON.stringify({status:findings.length?'FINDINGS':'PASS_WITH_LIMITS',task:'W76 independent W72 client source-byte and durable part-memory review',oracleCases:ORACLE.cases.length,oracleSha256:oracleSha,candidateHashes:hashes,checks:outcomes.length,outcomes,findings,providerCalls:0,nativeCalls:0,serverRestarts:0},null,2));
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
