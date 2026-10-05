'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'_easy_claude_work/ai14h_generation3_runtime1');
const manifest=JSON.parse(fs.readFileSync(path.join(dir,'source-freeze.json'),'utf8'));
for(const [file,hash] of Object.entries(manifest.hashes))assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,file))).digest('hex'),hash,file+' immutable source');
const ai=fs.readFileSync(path.join(dir,'js/spb-pro-ai.js'),'utf8'),state=fs.readFileSync(path.join(dir,'paint-booth-2-state-zones.js'),'utf8');
function slice(s,a,b){let x=s.indexOf(a),y=s.indexOf(b,x+a.length);assert(x>=0&&y>x,a);return s.slice(x,y);}
function hash(m){let h=2166136261;for(const v of m)h=Math.imul(h^(v&255),16777619);return m.length+':'+(h>>>0).toString(36);}
function world(){
 const mask=new Uint8Array(4096);mask.fill(255,0,128);
 const w={console,Uint8Array,Math,JSON,Object,Array,String,Number,Promise,Date,source:{generation:4,path:'C:/cars/fixture.psd',fingerprint:'fp-A',width:64,height:64},kind:'file',loading:false,committed:true,layout:'layout-A',element:'',_editReg:{},_editRegSig:'shape-A',_editRegPendingBefore:{},_partMemoryRuntime:null,
  zones:[],_psdLayers:[{id:'body',name:'Car Paint',visible:true,opacity:100,locked:false}],selectedZoneIndex:0,nextLinkGroupId:1,activeSpecChannel:'all'};
 w.window=w;w.CAR={signature:()=> 'shape-A',layoutSig:()=>w.layout,maskFor:()=>w.partMask?{mask:w.partMask}:null};w.partMask=mask;
 w.SpbProElements={sig:()=>w.element};w.Z={findLayer:v=>w._psdLayers.find(l=>l.id===v||l.name===v)};
 w.zoneSourceLayerIds=z=>(z.sourceLayers||[]).map(v=>w.Z.findLayer(v)?.id).filter(Boolean);
 w.getCurrentSourcePaintFile=()=>w.kind==='browser-file'?'C:/old/engine-target.png':w.source.path;
 w.SPBSourceLoadTransaction={getGeneration:()=>w.source.generation,getCommittedGeneration:()=>w.source.generation,getCommittedPath:()=>w.source.path,getCommittedFingerprint:()=>w.source.fingerprint,getCommittedKind:()=>w.kind,isLoading:()=>w.loading,isCommitted:()=>w.committed&&!w.loading};
 w.document={getElementById:id=>id==='paintCanvas'?{width:w.source.width,height:w.source.height}:{value:'',checked:false}};
 const noop=()=>{};Object.assign(w,{_savedMaskCanvasSize:()=>({w:64,h:64}),_savedMaskExpectedSize:()=>({w:64,h:64}),_getActiveImportedSpecMapPath:()=>'',_newZoneId:()=> 'new-id',_encodeSavedMask:m=>m?{width:64,height:64,data:[...m]}:null,_decodeSavedMask:m=>m?.data?new Uint8Array(m.data):null,_cloneUint8ArrayLike:x=>x,updateWearDisplay:noop,toggleNightBoostSlider:noop,updateOutputPath:noop,_sanitizeZonesInPlace:noop,renderZones:noop,renderZoneDetail:noop});
 w.SPBSourceLayerLinks={snapshotBindings:()=>({})};
 vm.createContext(w);for(const f of ['spb-ai-part-memory.js','spb-ai-part-memory-project.js'])vm.runInContext(fs.readFileSync(path.join(dir,'js',f),'utf8'),w);
 vm.runInContext(slice(ai,'function carSig()','function memNotes()')+slice(ai,'function scopedPartSourceNow()','function scopedPartProofCurrent(')+slice(ai,'function partMemoryHash(','function queueEditZones('),w);
 const z={id:'zone-roof',name:'Roof helper',base:'base::chrome',baseColorMode:'solid',baseColor:'#cc0000',useRegion:true,muted:false,regionMask:new Uint8Array(mask),sourceLayers:['body']};
 const bind={...w.source},r={island:'roof',layers:['Car Paint']};
 z._aiPartSource=bind;z._aiPartProv={r:JSON.stringify(r),z:hash(z.regionMask),p:hash(mask),l:w.layout,e:'',s:bind,car:'shape-A',layers:['body'],layerState:[{id:'body',visible:true,locked:false,opacity:100}]};
 w.zones=[z];w._editReg[w.editKey(r)]=z.name;w.ensurePartMemoryRuntime();
 vm.runInContext(slice(state,'function getConfig() {','function getSessionConfig()')+slice(state,'function loadConfigFromObj(cfg) {','// SHOKK / templates: session round-trip'),w);
 return w;
}
const results=[];
function test(id,fn){try{fn();results.push({id,pass:true});}catch(e){results.push({id,pass:false,error:e.stack});}}
function savedWorld(){const w=world(),cfg=w.getConfig();assert(cfg.zones[0].spbAIPartMemory,'actual save callback captured current owner');assert(!JSON.stringify(cfg.zones[0].spbAIPartMemory).includes('generation'));w.source={...w.source,generation:9};w.loadConfigFromObj(cfg);assert.equal(w.zones[0]._aiPartProv,undefined,'actual load grants no ownership');return {w,cfg};}
test('actual-save-load-fresh-generation-exact-owner',()=>{let{w}=savedWorld();let r=w.SpbAIPartMemoryRuntime.rebindAfterCommit(w.zones);assert.equal(r.rebound,1);let z=w.zones[0];assert.equal(z._aiPartProv.s.generation,9);assert.equal(z._aiPartProv.e,'');assert.equal(w._editReg[w.editKey(JSON.parse(z._aiPartProv.r))],z.name);assert(w.partOwnerCurrent(z,w.editKey(JSON.parse(z._aiPartProv.r))));});
for(const [id,change] of [
 ['fingerprint-replacement',w=>w.source.fingerprint='fp-B'],['path-replacement',w=>w.source.path='C:/cars/different.psd'],['canvas-size',w=>w.source.width=128],['pending-source',w=>w.loading=true],['unknown-source-bytes',w=>w.committed=false],['manual-mask',w=>w.zones[0].regionMask[0]=0],['changed-layout',w=>w.layout='layout-B'],['changed-element',w=>w.element='element-B'],['hidden-layer',w=>w._psdLayers[0].visible=false],['locked-layer',w=>w._psdLayers[0].locked=true],['missing-part-mask',w=>w.partMask=null],['duplicate-pending-selector',w=>w.zones.push({...w.zones[0],id:'other'})],['duplicate-id',w=>w.zones.push({...w.zones[0],muted:true})]
])test(id,()=>{let{w}=savedWorld();change(w);const r=w.SpbAIPartMemoryRuntime.rebindAfterCommit(w.zones);assert.equal(r.rebound,0);assert(w.zones.every(z=>!z._aiPartProv),'rejected records stay inert');});
test('save-does-not-adopt-current-source-for-stale-owner',()=>{const w=world();w.source={...w.source,generation:5};assert.equal(w.getConfig().zones[0].spbAIPartMemory,null);});
test('browser-selected-identity-ignores-legacy-engine-target',()=>{const w=world();w.kind='browser-file';w.source.path='browser-file:roof-car.png';const src=w.scopedPartSourceNow();assert.equal(src.path,w.source.path);});
const report={status:results.every(x=>x.pass)?'PASS':'FINDINGS',scope:'Actual integrated controller callbacks plus actual getConfig/loadConfig functions in VM; geometry and DOM services are controlled. No native/provider effects.',sourceHashes:manifest.hashes,results,providerCalls:0};
fs.writeFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_PART_MEMORY_INTEGRATED_RUNTIME_2026-10-04.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,passed:results.filter(x=>x.pass).length,total:results.length,failures:results.filter(x=>!x.pass)}));if(report.status!=='PASS')process.exitCode=1;
