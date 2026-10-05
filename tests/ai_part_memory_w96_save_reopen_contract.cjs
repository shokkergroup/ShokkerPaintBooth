'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),dir=path.join(root,'_easy_claude_work/ai14h_generation3_runtime5');
const pins={project:'763d36addca501256e1346d58b797d339b15666d04273cbf5c4840b15c1c6fc1',projectCandidate:'fff0127a7570c3fa8eaf2ad431f1ce2717763a2cd5b1688b15d18cc4f3c98d17',memory:'6e0d1e1466feca847d3a1c3300f32779ba610f3b6c72c7904a6c8fd97a6b3652',state:'710b4d8b1b7f229d334e06d1eb331ff48d9873a7cd139b276d2bab3ebfd591e7',ai:'60ae271c62d697ab31b9f2eed47b841a6038755db8f319507e38d03185ee3a21',aiCandidate:'9c46f0f1fb44c1f49b040273181f2c4ff73c52ee81c227a05589b4ba052c7323'};
const projectPath='_easy_claude_work/ai14h_w96_candidate/spb-ai-part-memory-project.js';
const aiCandidatePath='_easy_claude_work/ai14h_w96_candidate/spb-pro-ai.js';
const hashFile=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
const src={memory:path.join(dir,'js/spb-ai-part-memory.js'),state:path.join(dir,'paint-booth-2-state-zones.js')};
assert.equal(hashFile('_easy_claude_work/ai14h_generation3_runtime5/js/spb-ai-part-memory-project.js'),pins.project);
assert.equal(hashFile(projectPath),pins.projectCandidate);
for(const [k,p] of Object.entries(src))assert.equal(hashFile(path.relative(root,p)),pins[k]);
assert.equal(hashFile('_easy_claude_work/ai14h_generation3_runtime5/js/spb-pro-ai.js'),pins.ai);
assert.equal(hashFile(aiCandidatePath),pins.aiCandidate);
const project=fs.readFileSync(path.join(root,projectPath),'utf8'),memory=fs.readFileSync(src.memory,'utf8'),state=fs.readFileSync(src.state,'utf8'),ai=fs.readFileSync(path.join(root,aiCandidatePath),'utf8');
function slice(s,a,b){const i=s.indexOf(a),j=s.indexOf(b,i);assert(i>=0&&j>i,a);return s.slice(i,j);}
function maskHash(m){let h=2166136261;for(const v of m)h=Math.imul(h^(v&255),16777619);return m.length+':'+(h>>>0).toString(36);}
function world(){
 const partMask=new Uint8Array(4096);partMask.fill(255,0,128);
 const w={console,Uint8Array,Math,JSON,Object,Array,String,Number,Promise,Date,source:{generation:4,path:'C:/cars/fixture.psd',fingerprint:'file-sha256:'+'a'.repeat(64),width:64,height:64},kind:'layered',loading:false,committed:true,layout:'layout-A',element:'',_editReg:{},_editRegSig:'shape-A',_editRegPendingBefore:{},_partMemoryRuntime:null,
  zones:[],_psdLayers:[{id:'psd_0',name:'Car Paint',visible:true,opacity:100,locked:false}],selectedZoneIndex:0,nextLinkGroupId:1,activeSpecChannel:'all'};
 w.window=w;w.CAR={signature:()=> 'shape-A',layoutSig:()=>w.layout,maskFor:()=>w.partMask?{mask:w.partMask}:null};w.partMask=partMask;
 w.SpbProElements={sig:()=>w.element};w.Z={findLayer:v=>w._psdLayers.find(l=>l.id===v||l.name===v),footprint:()=>({share_pct:2.9,visible_pct:2.9})};
 w.zoneSourceLayerIds=z=>(z.sourceLayers||[]).map(v=>w.Z.findLayer(v)?.id).filter(Boolean);
 w.getCurrentSourcePaintFile=()=>w.source.path;
 w.SPBSourceLoadTransaction={getGeneration:()=>w.source.generation,getCommittedGeneration:()=>w.source.generation,getCommittedPath:()=>w.source.path,getCommittedFingerprint:()=>w.source.fingerprint,getCommittedKind:()=>w.kind,isLoading:()=>w.loading,isCommitted:()=>w.committed&&!w.loading};
 w.document={getElementById:id=>id==='paintCanvas'?{width:w.source.width,height:w.source.height}:{value:'',checked:false}};
 const noop=()=>{};Object.assign(w,{_savedMaskCanvasSize:()=>({w:64,h:64}),_savedMaskExpectedSize:()=>({w:64,h:64}),_getActiveImportedSpecMapPath:()=>'',_newZoneId:()=> 'new-id',_encodeSavedMask:m=>m?{width:64,height:64,data:[...m]}:null,_decodeSavedMask:m=>m?.data?new Uint8Array(m.data):null,_cloneUint8ArrayLike:x=>x,updateWearDisplay:noop,toggleNightBoostSlider:noop,updateOutputPath:noop,_sanitizeZonesInPlace:noop,renderZones:noop,renderZoneDetail:noop});
 w.SPBSourceLayerLinks={snapshotBindings:(z,layers)=>{
   if(z.sourceLayerBindings&&Object.keys(z.sourceLayerBindings).length)return z.sourceLayerBindings;
   const out={};(z.sourceLayers||[]).forEach(id=>{const l=(layers||[]).find(x=>String(x.id)===String(id));if(l)out[id]={parts:[l.name],key:JSON.stringify([l.name]),label:l.name,ambiguous:false};});return out;
 }};
 vm.createContext(w);vm.runInContext(memory,w);vm.runInContext(project,w);
 vm.runInContext(slice(ai,'    function carSig()','    function memNotes()')+slice(ai,'    function scopedPartSourceNow()','    function scopedPartProofCurrent(')+slice(ai,'    function scopedPartSelectorLayerIds(','    function scopedPartAppearance(')+slice(ai,'    function partMemoryHash(','    function queueEditZones('),w);
 const zoneMask=new Uint8Array(partMask),z={id:'zone-roof',name:'Roof helper',base:'base::gloss',finish:'f_gloss',baseColorMode:'solid',baseColor:'#1f8a3b',baseColorStrength:1,baseStrength:1,useRegion:true,muted:false,regionMask:zoneMask,sourceLayers:['psd_0'],sourceLayer:'psd_0',
  sourceLayerBindings:{psd_0:{parts:['Paintable Area','Car Paint'],key:'["Paintable Area","Car Paint"]',label:'Paintable Area / Car Paint',ambiguous:false}}};
 const bind={...w.source},r={island:'roof',layers:['Car Paint']};z._aiPartSource=bind;z._aiPartProv={r:JSON.stringify(r),z:maskHash(zoneMask),p:maskHash(partMask),l:w.layout,e:'',s:bind,car:'shape-A',layers:['psd_0'],layerState:[{id:'psd_0',visible:true,locked:false,opacity:100}]};
 w.zones=[z];w._editReg[w.editKey(r)]=z.name;w.ensurePartMemoryRuntime();
 vm.runInContext(slice(state,'function getConfig() {','function getSessionConfig()')+slice(state,'function loadConfigFromObj(cfg) {','// SHOKK / templates: session round-trip'),w);
 return w;
}
const rows=[];
function initialSaveReopen(){const w=world(),original=w.getConfig();assert(original.zones[0].spbAIPartMemory,'live owner save provides the record');w.source={...w.source,generation:9};w.loadConfigFromObj(original);assert(w.zones[0]._spbAIPartMemoryPending);assert.equal(w.zones[0]._aiPartProv,undefined);return {w,original};}
{
 const {w}=initialSaveReopen();w.CAR.maskFor=()=>null;w.layout='cold-layout';
 const retained=w.getConfig();assert(retained.zones[0].spbAIPartMemory,'cold CAR still serializes a matching inert pending record');
 assert.deepEqual(JSON.parse(JSON.stringify(retained.zones[0].spbAIPartMemory)),JSON.parse(JSON.stringify(w.zones[0]._spbAIPartMemoryPending)));
 assert.equal(w.zones[0]._aiPartProv,undefined,'capture never authorizes owner');
 assert(!JSON.stringify(retained.zones[0].spbAIPartMemory).includes('regionMask'),'no raw masks duplicated');
 rows.push({id:'actual-getConfig-cold-inert-retention',pass:true,recordBytes:JSON.stringify(retained.zones[0].spbAIPartMemory).length});
 w.loadConfigFromObj(retained);assert(w.zones[0]._spbAIPartMemoryPending,'actual loadConfigFromObj restages the inert record');assert.equal(w.zones[0]._aiPartProv,undefined);
 const refused=w.SpbAIPartMemoryRuntime.rebindAfterCommit(w.zones);assert.equal(refused.rebound,0,'cold/mismatched CAR proof must still refuse');assert(w.zones[0]._spbAIPartMemoryPending);assert.equal(w.zones[0]._aiPartProv,undefined);
 rows.push({id:'actual-load-and-fresh-proof-still-required',pass:true,rebound:refused.rebound,stillPending:true});
}
for(const [id,mutate] of [
 ['source-fingerprint',w=>{w.source.fingerprint='file-sha256:'+'b'.repeat(64);}],
 ['source-path',w=>{w.source.path='C:/cars/other.psd';}],
 ['source-dimensions',w=>{w.source.width=128;}],
 ['zone-id',w=>{w.zones[0].id='different-zone';}],
 ['zone-name',w=>{w.zones[0].name='Renamed';}],
 ['zone-mask',w=>{w.zones[0].regionMask[0]^=1;}],
 ['layer-binding',w=>{w.zones[0].sourceLayers=['missing-layer'];w.zones[0].sourceLayerBindings={};}],
 ['duplicate-short-layer-name',w=>{w._psdLayers.push({id:'psd_1',name:'Car Paint',visible:true,opacity:100,locked:false});}],
 ['muted-or-disabled',w=>{w.zones[0].muted=true;}],
 ['composite-only-source',w=>{w.source.fingerprint='composite-sha256:'+'c'.repeat(64);}],
 ['pending-load-not-committed',w=>{w.loading=true;}]
]){
 const {w}=initialSaveReopen();mutate(w);const cfg=w.getConfig();assert.equal(cfg.zones[0].spbAIPartMemory,null,id+' must drop inert pending record');rows.push({id,pass:true,dropped:true});
}
{
 const {w}=initialSaveReopen();w.CAR.maskFor=()=>({mask:w.partMask});w.layout='layout-A';
 const cfg=w.getConfig();assert(cfg.zones[0].spbAIPartMemory);
 w.loadConfigFromObj(cfg);const rebound=w.SpbAIPartMemoryRuntime.rebindAfterCommit(w.zones);
 assert.equal(rebound.rebound,1,'exact current source/mask/layout proof can activate after load');assert.equal(w.zones[0]._spbAIPartMemoryPending,undefined);assert(w.zones[0]._aiPartProv);
 rows.push({id:'later-matching-proof-rebinds',pass:true,rebound:rebound.rebound});
}
const report={work_item:'W96 private inert pending part-memory Save/Open retention',date:'2026-10-04',status:rows.every(x=>x.pass)?'PASS_WITH_LIMITS':'FAIL',oracle:{path:'_easy_claude_work/ai14h_w96_candidate/fresh-oracle.json',sha256:hashFile('_easy_claude_work/ai14h_w96_candidate/fresh-oracle.json'),cases:10,frozenBeforeSourceInspection:true},sources:{projectBase:{path:'_easy_claude_work/ai14h_generation3_runtime5/js/spb-ai-part-memory-project.js',sha256:pins.project},candidate:{path:projectPath,sha256:hashFile(projectPath)},memory:{path:'_easy_claude_work/ai14h_generation3_runtime5/js/spb-ai-part-memory.js',sha256:pins.memory},state:{path:'_easy_claude_work/ai14h_generation3_runtime5/paint-booth-2-state-zones.js',sha256:pins.state},controllerBase:{path:'_easy_claude_work/ai14h_generation3_runtime5/js/spb-pro-ai.js',sha256:pins.ai},controllerCandidate:{path:aiCandidatePath,sha256:hashFile(aiCandidatePath)}},counts:{actualSaveLoadCases:rows.length,passed:rows.filter(x=>x.pass).length,failed:rows.filter(x=>!x.pass).length,providers:0,native:0},rows,limits:['Actual Runtime5 getConfig()/loadConfigFromObj() and AI current-proof functions run in VM; CAR, DOM, source transaction, and layer-binding snapshot functions are deterministic controlled adapters.','The retained record is sanitized/inert and requires source path/fingerprint/dimensions, zone UUID/name, current region-mask hash, selector key, and layer IDs resolved uniquely by the controller against the live PSD layer table. This accepts the native-shaped selector Car Paint → psd_0 whose saved binding path is Paintable Area / Car Paint, while duplicate short names are dropped. It does not require CAR layout/mask readiness for inert persistence and does not authorize ownership.','Rebinding remains subject to unmodified fresh source, current zone/mask/layout/element/layer and unique-owner proofs. The native Car Paint path-binding shape is represented, but no native UI, PSD parser, full project file, or runtime installation acceptance is claimed.','No production source, native app, provider, browser, or server was changed/called.']};
fs.writeFileSync(path.join(root,'docs/handoff_reports/AI_HELPER_14H_PART_MEMORY_W96_CANDIDATE_2026-10-04.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,passed:report.counts.passed,total:report.counts.actualSaveLoadCases,report:report.sources.candidate.sha256,rows},null,2));if(report.status!=='PASS_WITH_LIMITS')process.exitCode=1;
