'use strict';
// W44 frozen behavior cases; actual source-transaction and Change File helpers,
// with document restoration, file IO and fingerprint IO controlled locally.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),folder=path.join(root,'_easy_claude_work/ai14h_w44_candidate');
const file=process.env.SPB_W44_CANDIDATE_SNAPSHOT||path.join(folder,'candidate/paint-booth-3-canvas.js'),bytes=fs.readFileSync(file),source=bytes.toString('utf8').replace(/\r\n/g,'\n');
const sha=crypto.createHash('sha256').update(bytes).digest('hex');
assert.equal(sha,process.env.SPB_W44_CANDIDATE_HASH||'98a3fa5390e89409913e519f1b77f39fb0dcb6d171d950fbcdc4356e9bf10679');
const oracle=JSON.parse(fs.readFileSync(path.join(folder,'oracle.json'),'utf8')).cases;assert.equal(oracle.length,12);
function slice(a,b){const i=source.indexOf(a),j=source.indexOf(b,i+a.length);assert(i>=0&&j>i);return source.slice(i,j);}
function world(hash){
 const w={window:{},Promise,Date,console};vm.createContext(w);
 const api=slice('            window.SPBSourceLoadTransaction = {','            };\n        }')+'            };';
 vm.runInContext(slice('        var _spbSourceLoadGeneration = 0;','        async function _spbFingerprintBytes')+api,w);
 w._spbRestoreSourceDocumentState=s=>vm.runInContext('_spbCommittedSourcePath='+JSON.stringify(s.committedPath)+';_spbCommittedSourceFingerprint='+JSON.stringify(s.committedFingerprint)+';',w);
 w._spbCaptureSourceDocumentState=()=>({});w._spbFingerprintBytes=hash||(()=>Promise.resolve('selected-content-sha256'));w.getCurrentSourcePaintFile=()=> 'C:/cars/upload.tga';
 vm.runInContext(slice('        function markFlatPaintLiveSource(','        function clearFlatPaintLiveSource(reason) {'),w);
 w.tx=w.window.SPBSourceLoadTransaction;
 w.metadata=(p,f)=>vm.runInContext('_spbCommittedSourcePath='+JSON.stringify(p)+';_spbCommittedSourceFingerprint='+JSON.stringify(f)+';',w);
 w.commit=()=>{const t=w.tx.begin('A');w.metadata('C:/A.tga','fp-a');w.tx.result(t,true);return t;};return w;
}
const rows=[];function test(index,fn){fn();rows.push({case:oracle[index],passed:true});}
const flush=async()=>{for(let i=0;i<16;i++)await Promise.resolve();};
(async()=>{
 test(0,()=>{const w=world();assert.equal(w.tx.isCommitted(),false);assert.equal(w.tx.getCommittedGeneration(),0);});
 test(1,()=>{const w=world();w.commit();w.tx.begin('B');assert.equal(w.tx.isCommitted(),false);assert.equal(w.tx.getCommittedPath(),'C:/A.tga');});
 test(2,()=>{const w=world(),t=w.tx.begin('A');w.metadata('C:/A.tga','fp-a');w.tx.result(t,true);assert.equal(w.tx.isCommitted(),true);assert.equal(w.tx.getCommittedGeneration(),t.generation);});
 test(3,()=>{const w=world(),a=w.commit(),b=w.tx.begin('B');w.tx.result(a,true);assert.equal(w.tx.isCommitted(),false);assert.equal(w.tx.getGeneration(),b.generation);});
 test(4,()=>{const w=world(),a=w.commit();w.tx.begin('B');w.tx.result(a,false);assert.equal(w.tx.isCommitted(),false);});
 test(5,()=>{const w=world();w.commit();const b=w.tx.begin('bad');w.tx.result(b,false);assert.equal(w.tx.isCommitted(),true);assert.equal(w.tx.getCommittedPath(),'C:/A.tga');assert.equal(w.tx.getCommittedGeneration(),b.generation);});
 test(6,()=>{const w=world();w.commit();w.tx.begin('B');w.tx.result(null,false);assert.equal(w.tx.isCommitted(),false);});
 test(7,()=>{const w=world(),a=w.tx.begin('A');w.metadata('C:/A.tga','');w.tx.result(a,true);assert.equal(w.tx.isCommitted(),false);});
 test(8,()=>{const w=world();w.commit();const old=w.tx.getGeneration();w.tx.begin('B');w.tx.restoreDocumentState({committedPath:'C:/A.tga',committedFingerprint:'fp-a'});assert.equal(w.tx.isCommitted(),true);assert(w.tx.getGeneration()>old);assert.equal(w.tx.getGeneration(),w.tx.getCommittedGeneration());});
 {
 const w=world();w.tx.begin('upload');let io=0;w.markFlatPaintLiveSource({name:'upload.png',arrayBuffer:()=>{io++;return Promise.resolve(new Uint8Array([1,2,3]).buffer);}},'test');assert.equal(w.tx.isCommitted(),false);await flush();assert.equal(io,1);assert.equal(w.tx.isCommitted(),true);assert.equal(w.tx.getCommittedFingerprint(),'selected-content-sha256');rows.push({case:oracle[9],passed:true});
 }
 {
 let resolve;const pending=new Promise(r=>resolve=r),w=world(()=>pending);w.tx.begin('upload-A');w.markFlatPaintLiveSource({name:'A.png',arrayBuffer:()=>Promise.resolve(new ArrayBuffer(1))},'test');await flush();const b=w.tx.begin('B');resolve('late-fp-a');await flush();assert.equal(w.tx.isCommitted(),false);assert.equal(w.tx.getGeneration(),b.generation);assert.equal(w.tx.getCommittedFingerprint(),'');rows.push({case:oracle[10],passed:true});
 }
 {
 const w=world(()=>Promise.reject(new Error('local hash failure')));w.tx.begin('upload');w.markFlatPaintLiveSource({name:'A.png',arrayBuffer:()=>Promise.resolve(new ArrayBuffer(1))},'test');await flush();assert.equal(w.tx.isCommitted(),false);rows.push({case:oracle[11],passed:true});
 }
 const report={utc:new Date().toISOString(),status:'CANDIDATE_PASS',candidate:{path:file,sha256:sha,installed:false},oracle,rows,counts:{passed:rows.length,total:oracle.length,provider_calls:0},limits:['Actual transaction and Change File helper functions run in a VM. Pixel commit, document restoration, file reads and byte fingerprint computation are modeled locally.','No native file picker, source loader, renderer, browser, server or provider ran. Flat-file integration and rollback require independent and native checks before promotion.']};
 const out=process.env.SPB_W44_REPORT_PATH||path.join(root,'docs/handoff_reports/AI_HELPER_14H_SOURCE_COMMIT_PROOF_CANDIDATE_2026-10-03.json');fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,passed:rows.length,total:oracle.length,candidate_sha256:sha}));
})().catch(e=>{console.error(e);process.exitCode=1;});
