'use strict';
const fs = require('fs');
const vm = require('vm');
const crypto = require('crypto');
const assert = require('assert');
const path = require('path');
const W53_COMPLETION_ORACLE = Object.freeze([
  { id: 'url-success-waits-for-selected-byte-proof', expect: 'loadPaintImageFromPath stays pending while current file bytes are unhashed, then resolves with committed identity' },
  { id: 'stale-url-A-rejects-without-touching-B', expect: 'superseded A rejects and cannot alter B path, fingerprint, or settled state' },
  { id: 'url-hash-failure-settles-and-rejects', expect: 'fingerprint failure settles loading, leaves no committed identity, and rejects caller' },
  { id: 'url-read-failure-settles-and-retains-A', expect: 'read failure rejects caller and leaves unchanged prior A committed at current generation' }
]);
assert.equal(W53_COMPLETION_ORACLE.length, 4);
const w50OracleFile = path.resolve(__dirname, '../_easy_claude_work/ai14h_w50_review/oracle.json');
const w50OracleBytes = fs.readFileSync(w50OracleFile);
assert.equal(crypto.createHash('sha256').update(w50OracleBytes).digest('hex'), '82eee6835d9d2bfe998db744f5cbc82e1acf28248ab6085041093db783d86644', 'W50 oracle must remain unchanged');
const w50Oracle = JSON.parse(w50OracleBytes.toString('utf8'));
assert.equal(w50Oracle.cases.length, 12);
const frozen = '_easy_claude_work/ai14h_w53_candidate/candidate/paint-booth-3-canvas.js';
const src = fs.readFileSync(frozen, 'utf8');
const actualHash = crypto.createHash('sha256').update(src).digest('hex');
assert.equal(actualHash, '159716b3150c785517bec3a1cf1b00a7318121885e7640276b5ffaf14fc91d9a', 'W53 isolated candidate bytes changed');
function declaration(name) {
  const re = new RegExp('(?:async\\s+)?function\\s+' + name + '\\s*\\(');
  const m = re.exec(src); assert(m, 'missing production function ' + name);
  let brace = src.indexOf('{', m.index), depth=0, quote='', esc=false, line=false, block=false, template=false;
  for (let i=brace;i<src.length;i++) {
    const c=src[i], n=src[i+1];
    if (line) { if(c==='\n') line=false; continue; }
    if (block) { if(c==='*'&&n==='/'){block=false;i++;} continue; }
    if (quote) { if(esc){esc=false;continue;} if(c==='\\'){esc=true;continue;} if(c===quote){quote='';template=false;} continue; }
    if(c==='/'&&n==='/'){line=true;i++;continue;} if(c==='/'&&n==='*'){block=true;i++;continue;}
    if(c==='"'||c==="'"||c==='`'){quote=c;template=c==='`';continue;}
    if(c==='{')depth++; else if(c==='}'&&--depth===0)return src.slice(m.index,i+1);
  }
  throw new Error('unclosed function '+name);
}
const code = ['_spbBeginSourceLoad','_spbIsCurrentSourceLoad','_spbSourceLoadResult','_spbFingerprintBytes','_spbFingerprintText','_spbDecodeImage','markFlatPaintLiveSource','browsePaintFile','loadPaintPreviewFromServer','openPaintFilePicker','loadPaintImageFromPath','loadPaintImageFromFileAsync'].map(declaration).join('\n') + `
window.SPBSourceLoadTransaction={begin:_spbBeginSourceLoad,isCurrent:_spbIsCurrentSourceLoad,result:_spbSourceLoadResult,getGeneration:()=>_spbSourceLoadGeneration,getCommittedGeneration:()=>_spbCommittedSourceGeneration,getCommittedKind:()=>_spbCommittedSourceKind,isLoading:()=>_spbSourceLoadPending,isCommitted:()=>!_spbSourceLoadPending&&_spbCommittedSourceGeneration===_spbSourceLoadGeneration&&_spbCommittedSourceGeneration>0&&!!_spbCommittedSourcePath&&!!_spbCommittedSourceFingerprint,getCommittedPath:()=>_spbCommittedSourcePath||'',getCommittedFingerprint:()=>_spbCommittedSourceFingerprint||''};`;
function harness(opts={}) {
  const nodes={}; let drawCount=0, commits=0, revoked=[], toasts=[], pickerConfig=null;
  const make=(id)=>nodes[id]||(nodes[id]={value:'',style:{},textContent:'',classList:{add(){},remove(){}},options:[],innerHTML:''});
  const canvas={width:4,height:4,getContext(){return {drawImage(){drawCount++},getImageData(){return {data:[]}}}}};
  if(opts.canvas!==false) nodes.paintCanvas=canvas;
  for(const id of ['iracingId','paintFile','driverName','regionCanvas','paintPreviewEmptyBig','paintPreviewEmpty2','paintPreviewLoaded','eyedropperInfo','paintDimensions','paintPreviewStatus','canvasInner','zoomControls'])make(id);
  const readers=[], images=[]; class FakeFile { constructor(_parts,name,meta){this.name=name;this.type=meta.type;this.size=3;this.arrayBuffer=()=>opts.fileBytes?opts.fileBytes():Promise.resolve(new Uint8Array([3,3,3]).buffer)} }
  class FR { constructor(){this.error=null;readers.push(this)} readAsDataURL(f){this.file=f} readAsArrayBuffer(f){this.file=f} }
  class Img { constructor(){images.push(this);this.width=12;this.height=8;this.naturalWidth=12;this.naturalHeight=8;} set src(v){this._src=v} get src(){return this._src} }
  const w={canvasMode:'eyedropper',activePaintTool:'brush',dispatchMode:'zone'};
  const ctx={window:w,document:{getElementById:id=>id==='paintCanvas'&&opts.canvas===false?null:(nodes[id]||null)},FileReader:FR,Image:Img,File:FakeFile,console:{log(){},error(){}},BASE_DRIVER_PATH:'root',validatePaintPath(){},showToast:(...x)=>toasts.push(x),decodeTGA(){throw new Error('unused')},loadDecodedImageToCanvas(){},_spbCommitSourceFile:(w,h,fn)=>{commits++;fn({drawImage(){drawCount++}})},setupCanvasHandlers(){},canvasZoom(){},toggleSplitView(){},setTimeout(){return 1},clearTimeout(){},splitViewActive:true,lastPreviewZoneHash:'',ctx:{},paintImageData:{old:true},_psdPath:null,ShokkerAPI:{baseUrl:'http://local'},_spbTransitionSourceMasks(){},_spbCaptureSourceDocumentState(){return {token:commits}},_spbRestoreSourceDocumentState(){},_spbUpdateLoadedCanvasUi(){},setCurrentSourcePaintFile(){},clearPSDDocumentState(){},URL:{createObjectURL(){return 'blob:test'+(revoked.length+1)},revokeObjectURL:u=>revoked.push(u)},openFilePicker:o=>{pickerConfig=o},fetch:async()=>({ok:true,blob:async()=>({size:3,type:'image/png',arrayBuffer:async()=>new Uint8Array([9,8,7]).buffer})}),JSON,Promise,Uint8Array,ArrayBuffer,TextEncoder,Date,Math,Object,String,Error,RegExp,Map,Set,Number,Boolean,parseInt,parseFloat,encodeURIComponent};
  vm.createContext(ctx); vm.runInContext(`var _spbSourceLoadGeneration=0,_spbCommittedSourcePath='',_spbCommittedSourceFingerprint='',_spbCommittedSourceGeneration=0,_spbSourceLoadPending=false,_spbCommittedSourceKind='file',_psdPath=null;`,ctx); vm.runInContext(code,ctx);
  return {ctx,w,nodes,readers,images,canvas,revoked,toasts,get pickerConfig(){return pickerConfig},get draws(){return drawCount},get commits(){return commits}, begin:(p,k)=>ctx._spbBeginSourceLoad(p,k)};
}
async function tick(){await Promise.resolve();await Promise.resolve();await new Promise(r=>setImmediate(r));}
(async()=>{
 const h=harness({canvas:false});
 const file={name:'B.png',size:3,type:'image/png',arrayBuffer:async()=>new Uint8Array([2,4,6]).buffer};
 h.ctx.browsePaintFile({files:[file]}); h.readers[0].onload({target:{result:'data:B'}}); h.images[0].onload();
 assert.equal(h.w.SPBSourceLoadTransaction.isLoading(),false,'missing-canvas request must settle');
 assert.equal(h.commits,0);
 const missingCanvasA=harness({canvas:false}); missingCanvasA.ctx._spbCommittedSourcePath='A.tga'; missingCanvasA.ctx._spbCommittedSourceFingerprint='fp-A'; missingCanvasA.ctx._spbCommittedSourceGeneration=0;
 missingCanvasA.ctx.browsePaintFile({files:[{name:'B.png'}]}); missingCanvasA.readers[0].onload({target:{result:'data:B'}}); missingCanvasA.images[0].onload();
 assert.equal(missingCanvasA.w.SPBSourceLoadTransaction.isLoading(),false); assert.equal(missingCanvasA.w.SPBSourceLoadTransaction.isCommitted(),true); assert.equal(missingCanvasA.w.SPBSourceLoadTransaction.getCommittedPath(),'A.tga');
 const m=harness();
 const b={name:'B.png',size:3,type:'image/png',arrayBuffer:async()=>new Uint8Array([2,4,6]).buffer};
 m.ctx.browsePaintFile({files:[b]}); m.readers[0].onload({target:{result:'data:B'}}); m.images[0].onload(); await tick();
 assert.equal(m.w.SPBSourceLoadTransaction.getCommittedPath(),'browser-file:B.png');
 const expectedFp=await m.ctx._spbFingerprintBytes(new Uint8Array([2,4,6]).buffer);
 assert.equal(m.w.SPBSourceLoadTransaction.getCommittedFingerprint(),expectedFp);
 assert.equal(m.w.SPBSourceLoadTransaction.isCommitted(),true);
 const staleImg=harness(); const sa={name:'A.png',size:1,arrayBuffer:async()=>new Uint8Array([1]).buffer}, sb={name:'B.png',size:1,arrayBuffer:async()=>new Uint8Array([2]).buffer};
 staleImg.ctx.browsePaintFile({files:[sa]}); staleImg.readers[0].onload({target:{result:'data:A'}});
 staleImg.ctx.browsePaintFile({files:[sb]}); staleImg.images[0].onload(); staleImg.readers[1].onload({target:{result:'data:B'}}); staleImg.images[1].onload(); await tick();
 assert.equal(staleImg.draws,1); assert.equal(staleImg.w.SPBSourceLoadTransaction.getCommittedPath(),'browser-file:B.png'); assert.deepEqual([staleImg.w.canvasMode,staleImg.w.activePaintTool,staleImg.w.dispatchMode],['eyedropper','brush','zone']);
 const noBytes=harness(); noBytes.ctx.browsePaintFile({files:[{name:'NoBytes.png'}]}); noBytes.readers[0].onload({target:{result:'data:unknown'}}); noBytes.images[0].onload(); await tick();
 assert.equal(noBytes.w.SPBSourceLoadTransaction.isLoading(),false); assert.equal(noBytes.w.SPBSourceLoadTransaction.isCommitted(),false);
 const race=harness();
 let releaseA; const a={name:'A.png',size:1,arrayBuffer:()=>new Promise(r=>releaseA=r)};
 race.ctx.browsePaintFile({files:[a]}); race.readers[0].onload({target:{result:'data:A'}}); race.images[0].onload();
 const bb={name:'B.png',size:1,arrayBuffer:async()=>new Uint8Array([22]).buffer};
 race.ctx.browsePaintFile({files:[bb]}); race.readers[1].onload({target:{result:'data:B'}}); race.images[1].onload(); await tick();
 const pathB=race.w.SPBSourceLoadTransaction.getCommittedPath(), fpB=race.w.SPBSourceLoadTransaction.getCommittedFingerprint();
 releaseA(new Uint8Array([11]).buffer); await tick();
 assert.equal(race.w.SPBSourceLoadTransaction.getCommittedPath(),pathB); assert.equal(race.w.SPBSourceLoadTransaction.getCommittedFingerprint(),fpB); assert.equal(pathB,'browser-file:B.png');
 let releasePathBytes, pathResolved=false; const pathLoad=harness({fileBytes:()=>new Promise(r=>releasePathBytes=r)}); pathLoad.ctx.fetch=async()=>({ok:true,blob:async()=>({type:'image/png'})});
 const pathResultPromise=pathLoad.ctx.loadPaintImageFromPath('/inbox/B.png').then(v=>{pathResolved=true;return v;},e=>{pathResolved=true;throw e;}); await tick(); pathLoad.readers[0].onload({target:{result:'data:pathB'}}); await tick(); pathLoad.images[0].onload(); await tick();
 assert.equal(pathResolved,false,'URL load Promise must remain pending until content fingerprint settles'); assert.equal(pathLoad.w.SPBSourceLoadTransaction.isLoading(),true);
 releasePathBytes(new Uint8Array([3,3,3]).buffer); const pathLoadResult=await pathResultPromise; assert.equal(pathLoadResult.name,'B.png'); assert.equal(pathLoad.w.SPBSourceLoadTransaction.isCommitted(),true);
 const hashFail=harness({fileBytes:()=>Promise.reject(new Error('hash failed'))}); hashFail.ctx.fetch=async()=>({ok:true,blob:async()=>({type:'image/png'})});
 const hashFailPromise=hashFail.ctx.loadPaintImageFromPath('/inbox/hash-fail.png'); await tick(); hashFail.readers[0].onload({target:{result:'data:hash-fail'}}); await tick(); hashFail.images[0].onload();
 await assert.rejects(hashFailPromise,/source proof|Failed to load/); assert.equal(hashFail.w.SPBSourceLoadTransaction.isLoading(),false); assert.equal(hashFail.w.SPBSourceLoadTransaction.isCommitted(),false);
 let resolveOldBytes, byteCall=0; const staleProgrammatic=harness({fileBytes:()=>++byteCall===1?new Promise(r=>resolveOldBytes=r):Promise.resolve(new Uint8Array([8,8]).buffer)});
 staleProgrammatic.ctx.fetch=async()=>({ok:true,blob:async()=>({type:'image/png'})});
 const oldPromise=staleProgrammatic.ctx.loadPaintImageFromPath('/inbox/A.png').then(v=>({value:v}),e=>({error:e})); await tick(); staleProgrammatic.readers[0].onload({target:{result:'data:oldA'}}); await tick(); staleProgrammatic.images[0].onload(); await tick();
 const newPromise=staleProgrammatic.ctx.loadPaintImageFromPath('/inbox/B.png'); await tick(); staleProgrammatic.readers[1].onload({target:{result:'data:newB'}}); await tick(); staleProgrammatic.images[1].onload(); await newPromise;
 const committedB={path:staleProgrammatic.w.SPBSourceLoadTransaction.getCommittedPath(),fingerprint:staleProgrammatic.w.SPBSourceLoadTransaction.getCommittedFingerprint()}; resolveOldBytes(new Uint8Array([7,7]).buffer); const oldResult=await oldPromise;
 assert(oldResult.error,'superseded URL loader must reject'); assert.equal(staleProgrammatic.w.SPBSourceLoadTransaction.getCommittedPath(),committedB.path); assert.equal(staleProgrammatic.w.SPBSourceLoadTransaction.getCommittedFingerprint(),committedB.fingerprint); assert.equal(staleProgrammatic.w.SPBSourceLoadTransaction.isLoading(),false);
 const urlReadFail=harness(); urlReadFail.ctx._spbCommittedSourcePath='A.tga'; urlReadFail.ctx._spbCommittedSourceFingerprint='fp-A'; urlReadFail.ctx._spbCommittedSourceGeneration=0;
 const urlReadPromise=urlReadFail.ctx.loadPaintImageFromPath('/inbox/B.tga'); await tick(); urlReadFail.readers[0].onerror(); await assert.rejects(urlReadPromise,/Failed to read/);
 assert.equal(urlReadFail.w.SPBSourceLoadTransaction.isLoading(),false); assert.equal(urlReadFail.w.SPBSourceLoadTransaction.isCommitted(),true); assert.equal(urlReadFail.w.SPBSourceLoadTransaction.getCommittedPath(),'A.tga');
 const u=harness(); u.nodes.paintFile.value='C:/old/A.tga'; u.ctx.openPaintFilePicker();
 assert.equal(u.pickerConfig.startPath,'C:/old');
 const urlPromise=u.pickerConfig.onSelect('C:/new/B.tga'); await tick();
 assert.equal(u.images.length,1,'URL decoder must use actual Image callback'); u.images[0].onload(); await urlPromise; assert.equal(u.w.SPBSourceLoadTransaction.getCommittedPath(),'C:/new/B.tga');
 assert.equal(u.w.SPBSourceLoadTransaction.getCommittedFingerprint(),await u.ctx._spbFingerprintBytes(new Uint8Array([9,8,7]).buffer));
 assert.deepEqual(u.revoked,['blob:test1']);
 const sr=harness(); let releaseUrlA; sr.ctx.fetch=async(_url,req)=>{const path=JSON.parse(req.body).path;return {ok:true,blob:async()=>({size:1,type:'image/png',arrayBuffer:()=>path.endsWith('/A.tga')?new Promise(r=>releaseUrlA=r):Promise.resolve(new Uint8Array([2,2]).buffer)})}};
 sr.ctx.openPaintFilePicker(); const pUrlA=sr.pickerConfig.onSelect('C:/src/A.tga'); await tick();
 const pUrlB=sr.pickerConfig.onSelect('C:/src/B.tga'); await tick(); assert.equal(sr.images.length,2); sr.images[1].onload(); await pUrlB; const urlPathB=sr.w.SPBSourceLoadTransaction.getCommittedPath();
 releaseUrlA(new Uint8Array([1,1]).buffer); sr.images[0].onload(); await pUrlA;
 assert.equal(urlPathB,'C:/src/B.tga'); assert.equal(sr.w.SPBSourceLoadTransaction.getCommittedPath(),urlPathB); assert.equal(sr.draws,1); assert.equal(sr.revoked.length,2);
 const uf=harness(); uf.ctx.fetch=async()=>({ok:true,blob:async()=>({size:1,type:'image/png',arrayBuffer:async()=>new Uint8Array([1]).buffer})});
 uf.ctx.openPaintFilePicker(); const ufPromise=uf.pickerConfig.onSelect('C:/bad.tga'); await tick(); uf.images[0].onerror(); await ufPromise; assert.equal(uf.w.SPBSourceLoadTransaction.isLoading(),false); assert.deepEqual(uf.revoked,['blob:test1']);
 const readFail=harness(); readFail.ctx._spbCommittedSourcePath='A.tga'; readFail.ctx._spbCommittedSourceFingerprint='fp-A'; readFail.ctx._spbCommittedSourceGeneration=0;
 readFail.ctx.browsePaintFile({files:[{name:'B.png'}]}); readFail.readers[0].onerror();
 assert.equal(readFail.w.SPBSourceLoadTransaction.isLoading(),false); assert.equal(readFail.w.SPBSourceLoadTransaction.isCommitted(),true); assert.equal(readFail.w.SPBSourceLoadTransaction.getCommittedPath(),'A.tga');
 const f=harness(); f.ctx._spbCommittedSourcePath='A.tga'; f.ctx._spbCommittedSourceFingerprint='fp-A'; f.ctx._spbCommittedSourceGeneration=0;
 f.ctx.browsePaintFile({files:[{name:'B.png'}]}); f.readers[0].onload({target:{result:'data:B'}}); f.images[0].onerror();
 assert.equal(f.w.SPBSourceLoadTransaction.isLoading(),false); assert.equal(f.w.SPBSourceLoadTransaction.isCommitted(),true); assert.equal(f.w.SPBSourceLoadTransaction.getCommittedPath(),'A.tga');
 console.log(JSON.stringify({candidate:actualHash,w50Oracle:{sha256:crypto.createHash('sha256').update(w50OracleBytes).digest('hex'),cases:w50Oracle.cases.length},w53CompletionOracle:W53_COMPLETION_ORACLE,missingCanvas:{loading:h.w.SPBSourceLoadTransaction.isLoading(),commits:h.commits},missingCanvasRetainedA:{ready:missingCanvasA.w.SPBSourceLoadTransaction.isCommitted(),path:missingCanvasA.w.SPBSourceLoadTransaction.getCommittedPath()},selectedB:{path:m.w.SPBSourceLoadTransaction.getCommittedPath(),fingerprint:m.w.SPBSourceLoadTransaction.getCommittedFingerprint(),committed:m.w.SPBSourceLoadTransaction.isCommitted()},lateImage:{draws:staleImg.draws,path:staleImg.w.SPBSourceLoadTransaction.getCommittedPath()},unknownBytes:{loading:noBytes.w.SPBSourceLoadTransaction.isLoading(),committed:noBytes.w.SPBSourceLoadTransaction.isCommitted()},lateHash:{path:pathB,stable:race.w.SPBSourceLoadTransaction.getCommittedFingerprint()===fpB},programmaticPath:{resolvedName:pathLoadResult.name,resolvedWhileProofPending:false,settled:pathLoad.w.SPBSourceLoadTransaction.isCommitted()},programmaticHashFailure:{rejected:true,loading:hashFail.w.SPBSourceLoadTransaction.isLoading(),committed:hashFail.w.SPBSourceLoadTransaction.isCommitted()},programmaticStaleA:{rejected:!!oldResult.error,retainedB:staleProgrammatic.w.SPBSourceLoadTransaction.getCommittedPath()===committedB.path},programmaticReadFailure:{loading:urlReadFail.w.SPBSourceLoadTransaction.isLoading(),retainedA:urlReadFail.w.SPBSourceLoadTransaction.getCommittedPath()},serverPicker:{ok:u.w.SPBSourceLoadTransaction.isCommitted(),path:u.w.SPBSourceLoadTransaction.getCommittedPath(),fingerprint:u.w.SPBSourceLoadTransaction.getCommittedFingerprint(),revoked:u.revoked},serverLateA:{path:urlPathB,retained:sr.w.SPBSourceLoadTransaction.getCommittedPath()===urlPathB,draws:sr.draws,revoked:sr.revoked.length},serverDecodeFailure:{ok:!uf.w.SPBSourceLoadTransaction.isCommitted(),loading:uf.w.SPBSourceLoadTransaction.isLoading(),revoked:uf.revoked},fileReadFailure:{loading:readFail.w.SPBSourceLoadTransaction.isLoading(),committed:readFail.w.SPBSourceLoadTransaction.isCommitted(),path:readFail.w.SPBSourceLoadTransaction.getCommittedPath()},failedB:{loading:f.w.SPBSourceLoadTransaction.isLoading(),committed:f.w.SPBSourceLoadTransaction.isCommitted(),path:f.w.SPBSourceLoadTransaction.getCommittedPath()},counts:{actualCallbacks:['browsePaintFile reader/image success/error','loadPaintImageFromPath/loadPaintImageFromFileAsync','openPaintFilePicker onSelect/loadPaintPreviewFromServer','markFlatPaintLiveSource','transaction helpers'],providerCalls:0,nativeCalls:0}},null,2));
})().catch(e=>{console.error(e.stack||e);process.exitCode=1});















