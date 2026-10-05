'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const { TextEncoder } = require('node:util');
const canvasPath = '_easy_claude_work/ai14h_tga_consumer_candidate/paint-booth-3-canvas.js';
const guardPath = '_easy_claude_work/ai14h_final_source_identity_candidate/browser-file-v2/spb-pro-ai.js';
const oraclePath = '_easy_claude_work/ai14h_w120_part_memory_source_identity/canvas-consumer-oracle.json';
const canvas = fs.readFileSync(canvasPath, 'utf8');
const guardSource = fs.readFileSync(guardPath, 'utf8');
const oracleText = fs.readFileSync(oraclePath, 'utf8').replace(/^\uFEFF/, '');
const oracle = JSON.parse(oracleText);
const sha = s => crypto.createHash('sha256').update(s).digest('hex').toUpperCase();
const hashBytes = b => crypto.createHash('sha256').update(Buffer.from(b)).digest('hex');
function extract(source, name) {
  const normal = source.indexOf(`function ${name}(`), asyncStart = source.indexOf(`async function ${name}(`);
  const start = asyncStart >= 0 && (normal < 0 || asyncStart < normal) ? asyncStart : normal; assert(start >= 0, `${name} exists`);
  const brace = source.indexOf('{', start); let depth = 0, q = null, esc = false, line = false, block = false;
  for (let i = brace; i < source.length; i++) {
    const c = source[i], n = source[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (q) { if (esc) esc = false; else if (c === '\\') esc = true; else if (c === q) q = null; continue; }
    if (c === '/' && n === '/') { line = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '{') depth++; else if (c === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`unterminated ${name}`);
}
const guardFn = extract(guardSource, 'durablePartMemorySourceIdentityCurrent');
const gctx = vm.createContext({ String, RegExp });
vm.runInContext(`${guardFn}; this.guard=durablePartMemorySourceIdentityCurrent;`, gctx);
function harness(opts = {}) {
  const pCanvas = { width:0, height:0, getContext:()=>({ drawImage(){}, getImageData:(x,y,w,h)=>({width:w,height:h,data:new Uint8ClampedArray(w*h*4)}) }) };
  const rCanvas = { width:0, height:0 };
  const fileRevokes = [];
  function Img() { this.naturalWidth=64; this.naturalHeight=64; this.width=64; this.height=64; }
  Object.defineProperty(Img.prototype, 'src', { set(v) { this._src=v; if(this.onload)this.onload(); }, get(){return this._src;} });
  const document = { getElementById(id) { return id==='paintCanvas'?pCanvas:id==='regionCanvas'?rCanvas:null; } };
  const context = vm.createContext({
    console, Promise, Date, Math, JSON, Object, Array, String, Number, RegExp, Error, Uint8Array, Uint8ClampedArray,
    TextEncoder, crypto: opts.noCrypto ? undefined : crypto.webcrypto, Image:Img, document, ShokkerAPI:{baseUrl:'http://test'},
    URL:{createObjectURL:()=>`blob:test-${Math.random()}`,revokeObjectURL:u=>fileRevokes.push(u)},
    setTimeout:()=>0, fetch: opts.fetch || (async()=>({ok:true,headers:{get:()=>opts.header||''},blob:async()=>({size:3,type:'image/png',arrayBuffer:async()=>Buffer.from([9,8,7])})})),
    _spbSourceLoadGeneration:0,_spbSourceLoadPending:false,_spbCommittedSourceGeneration:0,_spbCommittedSourceKind:'file',
    _spbCommittedSourcePath:'',_spbCommittedSourceFingerprint:'',_psdPath:null,paintImageData:null,splitViewActive:true,
    _spbCaptureSourceDocumentState:()=>({}),_spbRestoreSourceDocumentState:()=>{},_spbTransitionSourceMasks:()=>{},
    _spbUpdateLoadedCanvasUi:()=>{},setCurrentSourcePaintFile:()=>{},clearPSDDocumentState:()=>{},
    showToast:()=>{},triggerPreviewRender:()=>{}
  });
  context.window=context;
  const names=['_spbBeginSourceLoad','_spbIsCurrentSourceLoad','_spbSourceLoadResult','_spbFingerprintBytes','_spbFingerprintText','_spbDecodeImage','loadPaintPreviewFromServer','markFlatPaintLiveSource'];
  vm.runInContext(names.map(n=>extract(canvas,n)).join('\n')+`\nthis.API={begin:_spbBeginSourceLoad,isCurrent:_spbIsCurrentSourceLoad,result:_spbSourceLoadResult,get kind(){return _spbCommittedSourceKind},get path(){return _spbCommittedSourcePath},get fingerprint(){return _spbCommittedSourceFingerprint},get generation(){return _spbCommittedSourceGeneration},get pending(){return _spbSourceLoadPending},preview:loadPaintPreviewFromServer,mark:markFlatPaintLiveSource};`, context, {filename:canvasPath});
  return { context, api:context.API, paint:pCanvas, region:rCanvas, revokes:fileRevokes };
}
(async()=>{
  const rows=[];
  // Header-backed server TGA: current pixels are decoded from preview but identity is the attested source TGA bytes.
  const headerDigest='a'.repeat(64), previewBytes=Buffer.from([1,2,3,4]);
  const h=harness({header:headerDigest,fetch:async()=>({ok:true,headers:{get:n=>n==='X-Source-Bytes-SHA256'?headerDigest:''},blob:async()=>({size:4,type:'image/png',arrayBuffer:async()=>previewBytes})})});
  const hr=await h.api.preview('C:/paint/car.tga');
  assert.equal(hr.ok,true); assert.equal(h.api.kind,'flat'); assert.equal(h.api.path,'C:/paint/car.tga'); assert.equal(h.api.fingerprint,'file-sha256:'+headerDigest); assert.equal(h.api.pending,false); assert.equal(gctx.guard(h.api.kind,h.api.fingerprint,h.api.path),true);
  rows.push({id:'preview-header-sha',result:'PASS',kind:h.api.kind,path:h.api.path,fingerprint:h.api.fingerprint,durableGuard:true});
  // Headerless/invalid header remains a successful current-session preview but cannot pass durable byte identity.
  for(const item of [{id:'preview-headerless',header:''},{id:'preview-malformed-header',header:'A'.repeat(64)}]){
    const x=harness({header:item.header,fetch:async()=>({ok:true,headers:{get:()=>item.header},blob:async()=>({size:4,type:'image/png',arrayBuffer:async()=>previewBytes})})});
    const r=await x.api.preview('C:/paint/car.tga'); assert.equal(r.ok,true); assert.equal(x.api.kind,'flat'); assert.equal(x.api.pending,false); assert(!x.api.fingerprint.startsWith('file-sha256:')); assert.equal(gctx.guard(x.api.kind,x.api.fingerprint,x.api.path),false);
    rows.push({id:item.id,result:'PASS',kind:x.api.kind,path:x.api.path,fingerprint:x.api.fingerprint,durableGuard:false});
  }
  // Starting B while A is waiting on fetch prevents late A from changing the committed identity.
  let releaseA; const promiseA=new Promise(resolve=>releaseA=resolve); const digestA='b'.repeat(64), digestB='c'.repeat(64);
  const race=harness({fetch:async(_url,request)=>{const p=JSON.parse(request.body).path;if(p==='A.tga')return promiseA;return {ok:true,headers:{get:n=>n==='X-Source-Bytes-SHA256'?digestB:''},blob:async()=>({size:3,type:'image/png',arrayBuffer:async()=>Buffer.from([2,2,2])})};}});
  const pa=race.api.preview('A.tga'); await Promise.resolve(); const rb=await race.api.preview('B.tga'); assert.equal(rb.ok,true); releaseA({ok:true,headers:{get:n=>n==='X-Source-Bytes-SHA256'?digestA:''},blob:async()=>({size:3,type:'image/png',arrayBuffer:async()=>Buffer.from([1,1,1])})}); const ra=await pa;
  assert.equal(ra.ok,false); assert.equal(race.api.path,'B.tga'); assert.equal(race.api.fingerprint,'file-sha256:'+digestB); assert.equal(race.api.kind,'flat'); assert.equal(race.api.pending,false);
  rows.push({id:'preview-stale-response',result:'PASS',lateAOk:ra.ok,finalPath:race.api.path,finalFingerprint:race.api.fingerprint});
  // Browser-selected File bytes must use exact File.arrayBuffer SHA-256 and actual committed kind/path.
  const browser=harness(); const tx=browser.api.begin('car.tga','flat-file'); const raw=Buffer.from([10,20,30,40]); const file={name:'car.tga',size:4,type:'image/x-tga',arrayBuffer:async()=>raw};
  assert.equal(await browser.api.mark(file,'file-picker',tx),true); assert.equal(browser.api.kind,'browser-file'); assert.equal(browser.api.path,'browser-file:car.tga'); assert.equal(browser.api.fingerprint,'file-sha256:'+hashBytes(raw)); assert.equal(gctx.guard(browser.api.kind,browser.api.fingerprint,browser.api.path),true); assert.equal(browser.api.pending,false);
  rows.push({id:'browser-file-exact-bytes',result:'PASS',kind:browser.api.kind,path:browser.api.path,fingerprint:browser.api.fingerprint,durableGuard:true});
  // Legacy environments use a non-SHA fallback: source stays committed for the session but durable guard refuses it.
  const weak=harness({noCrypto:true}); const txw=weak.api.begin('car.tga','flat-file'); assert.equal(await weak.api.mark(file,'file-picker',txw),true); assert(weak.api.fingerprint.startsWith('fnv1a32-')); assert.equal(gctx.guard(weak.api.kind,weak.api.fingerprint,weak.api.path),false);
  rows.push({id:'browser-file-weak-hash',result:'PASS',fingerprint:weak.api.fingerprint,durableGuard:false});
  // A delayed browser-file hash cannot overwrite a newer commit.
  let releaseFile; const lateBytes=new Promise(resolve=>releaseFile=resolve); const stale=harness(); const oldTx=stale.api.begin('old.tga','flat-file'); const oldFile={name:'old.tga',arrayBuffer:()=>lateBytes}; const oldResult=stale.api.mark(oldFile,'old-read',oldTx); const newTx=stale.api.begin('new.png','flat-file'); const newFile={name:'new.png',arrayBuffer:async()=>Buffer.from([5,5,5])}; assert.equal(await stale.api.mark(newFile,'new-read',newTx),true); releaseFile(Buffer.from([4,4,4])); assert.equal(await oldResult,false); assert.equal(stale.api.kind,'browser-file'); assert.equal(stale.api.path,'browser-file:new.png'); assert.equal(stale.api.fingerprint,'file-sha256:'+hashBytes(Buffer.from([5,5,5])));
  rows.push({id:'browser-file-stale-read',result:'PASS',finalPath:stale.api.path,finalFingerprint:stale.api.fingerprint});
  // No byte reader is not a durable source. The transaction settles failed and fingerprint stays blank.
  const bad=harness(); const badTx=bad.api.begin('bad.tga','flat-file'); assert.equal(await bad.api.mark({name:'bad.tga'},'file-picker',badTx),false); assert.equal(bad.api.fingerprint,''); assert.equal(bad.api.pending,false); assert.equal(bad.api.generation,0);
  rows.push({id:'browser-file-unreadable',result:'PASS',path:bad.api.path,fingerprint:bad.api.fingerprint,pending:bad.api.pending,committedGeneration:bad.api.generation});
  const report={workItem:'W120 independent W112 canvas consumer review',status:'PASS_PRIVATE_FUNCTION_REPLAY',source:{path:canvasPath,sha256:sha(canvas),guard:{path:guardPath,sha256:sha(guardSource)}},oracle:{path:oraclePath,sha256:sha(oracleText),cases:oracle.cases.length,frozenBeforeDynamicReplay:true},cases:rows,limits:['Executed exact extracted loadPaintPreviewFromServer and markFlatPaintLiveSource plus their exact source transaction/fingerprint/decode helpers in a VM with fake fetch/DOM/Image/File services. Actual raster draw and backend are stubbed; no browser or native app.','Header correctness is a producer contract and was not re-proven here; parent W112 backend has separate snapshot/header tests.','The test proves hash/path/kind propagation, consumer race refusal, and headerless durable-denial behavior, not correct visual TGA decoding or persisted-project restore.']};
  const out='docs/handoff_reports/AI_HELPER_14H_TGA_CONSUMER_W120_REVIEW_2026-10-04.json'; fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');
  assert.equal(rows.length,8); console.log(JSON.stringify({status:report.status,cases:rows.length,passed:rows.filter(r=>r.result==='PASS').length,sourceHash:report.source.sha256,report:out},null,2));
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
