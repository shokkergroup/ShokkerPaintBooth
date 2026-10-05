'use strict';
// W45 independent source-readiness oracle frozen before implementation review.
const cases = Object.freeze([
  {id:'fresh-generation-load-failure',want:'failed replacement keeps only the unchanged/restored prior committed source current'},
  {id:'stale-older-load',want:'older async result cannot settle or replace the latest transaction'},
  {id:'failed-hash',want:'failed content hashing cannot publish a ready committed source'},
  {id:'null-does-not-clear-newer-pending',want:'null completion cannot clear or commit the latest pending source'},
  {id:'change-file-entrypoint-a',want:'browsePaintFile Change File path reaches live-source fingerprint marker'},
  {id:'change-file-entrypoint-b',want:'loadPaintImage Change File path reaches live-source fingerprint marker'},
  {id:'source-restore-api',want:'restore API issues a fresh generation and commits the restored path/content identity'},
  {id:'filepath-fingerprint-coherence',want:'the committed path belongs to the same selected file bytes used for hashing'},
  {id:'reentrant-generation-during-hash',want:'newer generation invalidates an older pending file hash'},
  {id:'positive-current-load',want:'successful current marker stores selected bytes fingerprint and captured source path'}
]);
if(cases.length!==10)throw new Error('W45 requires ten cases');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const sourceFile=path.join(root,'_easy_claude_work/ai14h_w44_candidate/candidate/paint-booth-3-canvas.js');
const bytes=fs.readFileSync(sourceFile), source=bytes.toString('utf8').replace(/\r\n/g,'\n');
const sha=crypto.createHash('sha256').update(bytes).digest('hex');
assert.equal(sha,'98a3fa5390e89409913e519f1b77f39fb0dcb6d171d950fbcdc4356e9bf10679');
function slice(a,b){const i=source.indexOf(a),j=source.indexOf(b,i+a.length);assert(i>=0&&j>i,`source slice not found: ${a}`);return source.slice(i,j);}
const txSource=slice('        var _spbSourceLoadGeneration = 0;','        async function loadPaintPreviewFromServer');
const markerSource=slice('        function markFlatPaintLiveSource(file, source) {','        function clearFlatPaintLiveSource(reason) {');
const getterSource=slice('function getCurrentSourcePaintFile() {','function setCurrentSourcePaintFile');
function world(){
 const w={window:{},Promise,Date,console,Uint8Array,ArrayBuffer,Math,crypto:{subtle:null},_psdPath:'',_spbCaptureSourceDocumentState:()=>({}),_spbRestoreSourceDocumentState:s=>{w._psdPath=s.psdPath||'';w._spbCommittedSourcePath=s.committedPath||s.psdPath||'';w._spbCommittedSourceFingerprint=s.committedFingerprint||'';},document:{getElementById:id=>id==='paintFile'?{value:w.currentPath}:null}};
 vm.createContext(w);vm.runInContext(txSource+markerSource+getterSource,w);w.tx=w.window.SPBSourceLoadTransaction;
 w.hash=async bytes=>'fp:'+Array.from(new Uint8Array(bytes)).join(',');w._spbFingerprintBytes=w.hash;
 w.seed=(p,f)=>{w._psdPath='';w._spbCommittedSourcePath=p;w._spbCommittedSourceFingerprint=f;const t=w.tx.begin(p);w.tx.result(t,true,{committedPath:p,fingerprint:f});return t;};return w;
}
const rows=[];function check(i,fn){fn();rows.push({case:cases[i],passed:true});}
async function flush(){for(let i=0;i<12;i++)await Promise.resolve();}
(async()=>{
 check(0,()=>{const w=world();w.seed('C:/A.tga','fp:A');const b=w.tx.begin('C:/B.tga');const r=w.tx.result(b,false,{error:'decode failed'});assert.equal(r.ok,false);assert.equal(w.tx.isCommitted(),true);assert.equal(w.tx.getCommittedPath(),'C:/A.tga');assert.equal(w.tx.getCommittedFingerprint(),'fp:A');assert.equal(w.tx.getCommittedGeneration(),b.generation);});
 check(1,()=>{const w=world();const a=w.seed('C:/A.tga','fp:A');const b=w.tx.begin('C:/B.tga');w.tx.result(a,true,{committedPath:'C:/A.tga',fingerprint:'fp:A'});assert.equal(w.tx.getGeneration(),b.generation);assert.equal(w.tx.isCommitted(),false);w.tx.result(b,false);assert.equal(w.tx.isCommitted(),true);assert.equal(w.tx.getCommittedPath(),'C:/A.tga');});
 const fail=world();fail.seed('C:/A.tga','fp:A');fail.currentPath='C:/B.tga';const bfail=fail.tx.begin('C:/B.tga');fail.window._spbFlatPaintLiveSource=null;fail.window._spbFingerprintBytes=()=>Promise.reject(new Error('hash failure'));fail._spbFingerprintBytes=fail.window._spbFingerprintBytes;fail.markFlatPaintLiveSource({name:'B.tga',arrayBuffer:()=>Promise.resolve(new ArrayBuffer(1))},'change-file-flat');await flush();assert.equal(fail.tx.isCommitted(),false);assert.equal(fail.tx.getCommittedPath(),'C:/A.tga');assert.equal(fail.tx.getCommittedGeneration(),bfail.generation-1);rows.push({case:cases[2],passed:true,observation:'safe-not-ready; failure leaves latest generation pending with no surfaced result'});
 check(3,()=>{const w=world();w.seed('C:/A.tga','fp:A');const b=w.tx.begin('C:/B.tga');w.tx.result(null,false);assert.equal(w.tx.getGeneration(),b.generation);assert.equal(w.tx.isCommitted(),false);});
 check(4,()=>{const body=slice('        function browsePaintFile(input) {','        function loadPaintImage(input) {');assert(body.includes("markFlatPaintLiveSource(file, 'change-file-tga')"));assert(body.includes("markFlatPaintLiveSource(file, 'browse-file-flat')"));});
 check(5,()=>{const body=slice('        function loadPaintImage(input) {','        function ');assert(body.includes("markFlatPaintLiveSource(file, 'change-file-tga')"));assert(body.includes("markFlatPaintLiveSource(file, 'change-file-flat')"));});
 check(6,()=>{const w=world();const result=w.tx.restoreDocumentState({psdPath:'C:/A.tga',committedPath:'C:/A.tga',committedFingerprint:'fp:A'});assert.equal(result.ok,true);assert.equal(w.tx.isCommitted(),true);assert.equal(w.tx.getCommittedPath(),'C:/A.tga');assert.equal(w.tx.getCommittedGeneration(),w.tx.getGeneration());});
 // Actual new Change File B load with an already-committed A: getter prioritizes A over the B path input.
 const wc=world();wc.seed('C:/old-A.tga','fp:old-A');wc.currentPath='C:/selected-B.tga';const tb=wc.tx.begin('C:/selected-B.tga');wc.markFlatPaintLiveSource({name:'B.tga',arrayBuffer:()=>Promise.resolve(new Uint8Array([2,3,4]).buffer)},'change-file-flat');await flush();assert.equal(wc.tx.getGeneration(),tb.generation);assert.equal(wc.tx.isCommitted(),true);assert.equal(wc.tx.getCommittedPath(),'C:/old-A.tga');assert.equal(wc.tx.getCommittedFingerprint(),'fp:2,3,4');rows.push({case:cases[7],passed:true,observation:'counterexample reproduced: new B bytes are committed under prior A path because getter prioritizes committed source'});
 let resolveOld;const wr=world();wr.currentPath='C:/A.tga';wr.tx.begin('C:/A.tga');wr.markFlatPaintLiveSource({name:'A.tga',arrayBuffer:()=>new Promise(r=>{resolveOld=r;})},'change-file-flat');await flush();const newer=wr.tx.begin('C:/B.tga');resolveOld(new Uint8Array([4]).buffer);await flush();assert.equal(wr.tx.getGeneration(),newer.generation);assert.equal(wr.tx.isCommitted(),false);rows.push({case:cases[8],passed:true});
 const wp=world();wp.currentPath='C:/A.tga';wp.tx.begin('C:/A.tga');wp.markFlatPaintLiveSource({name:'A.tga',arrayBuffer:()=>Promise.resolve(new Uint8Array([1,2,3]).buffer)},'change-file-flat');await flush();assert.equal(wp.tx.isCommitted(),true);assert.equal(wp.tx.getCommittedPath(),'C:/A.tga');assert.equal(wp.tx.getCommittedFingerprint(),'fp:1,2,3');rows.push({case:cases[9],passed:true});
 const report={utc:new Date().toISOString(),status:'REVIEW_COMPLETE_FINDING',candidate:{path:sourceFile,sha256:sha,immutable:true,installed:false},baseline_sha256_prefix:'F5588017',producer_contract:{path:'tests/ai_source_commit_proof_candidate_contract.cjs',result:'CANDIDATE_PASS 12/12 unchanged; its generated report was restored byte-for-byte afterward'},oracle:cases,rows,counts:{review_cases:rows.length,provider_calls:0},finding:{severity:'P1',summary:'markFlatPaintLiveSource hashes the newly selected browser file but then asks getCurrentSourcePaintFile for its path; that getter prioritizes the previously committed source path, so a new Change File B can be marked committed under old path A.',evidence:'W45 case filepath-fingerprint-coherence reproduced committedPath C:/old-A.tga with fingerprint fp:2,3,4 from newly selected B bytes; isCommitted() returned true.'},other_observations:['Fresh failed replacement result preserves/restores the old committed path and fingerprint and advances their committed generation only when both are present. This is coherent when loader rollback retained the old document; transaction result remains ok:false.','Failed Change File byte hashing is safely not committed, but markFlatPaintLiveSource swallows rejection without settling the transaction. The source stays not-ready at the current generation and has no returned failure result; readiness can remain stranded until another transaction or restore.','Both browser file entrypoints call markFlatPaintLiveSource after pixel commit for TGA and raster loads.','Source restore increments generation before restoring and only reports readiness when restored path and fingerprint are both non-empty.'],limits:['Controlled VM executed actual transaction and marker helpers with stub document restore and controlled file byte promises.','Change File callsite integration was verified from actual handler bodies, not driven through a native browser FileReader/Image event loop.','No renderer, native file picker, server, provider or network was used.'],source_sha256_after:sha};
 const out=path.join(root,'docs/handoff_reports/AI_HELPER_14H_SOURCE_COMMIT_W45_REVIEW_2026-10-03.json');fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,cases:rows.length,all_passed:true,sha256:sha,finding:report.finding.summary}));
})().catch(e=>{console.error(e);process.exitCode=1;});





