'use strict';
// W93 independently replays the current owner proof with real controller
// functions and real E.plan/E.compile. Oracle was frozen before source review.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const cpath='_easy_claude_work/ai14h_w89_review/candidate/spb-pro-ai.js';
const epath='_easy_claude_work/ai14h_w89_review/candidate/spb-pro-edit.js';
const dpath='_easy_claude_work/ai14h_w89_review/base/spb-pro-design.js';
const oraclePath='_easy_claude_work/ai14h_w93_review/fresh-oracle.json';
const pins={controller:'fa51053ad77409aa677a9e2d8ef633fd6d6bcd20e5dcdf5628af40c65b37dc59',edit:'3696cf6c9bdf9a28a056ebf90a9ddd23cfe290134943c11beb4c7ec5485a173a',design:'0533393ff5f2170236f60d4ed489c7ae52f98805e12b0764da67a967f756f2e8',oracle:'1d7655a63318d8384ec3e93a1ba4c5009f0635262b5f242ab1469ad85c7c4169'};
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const bytes={c:fs.readFileSync(path.join(root,cpath),'utf8'),e:fs.readFileSync(path.join(root,epath),'utf8'),d:fs.readFileSync(path.join(root,dpath),'utf8')};
for(const [k,p] of [['c',cpath],['e',epath],['d',dpath]])assert.equal(hash(Buffer.from(bytes[k])),pins[k==='c'?'controller':k==='e'?'edit':'design'],`pinned ${k} source changed`);
const oracleBytes=fs.readFileSync(path.join(root,oraclePath));assert.equal(hash(oracleBytes),pins.oracle);const oracle=JSON.parse(oracleBytes);assert.equal(oracle.case_count,12);
function slice(src,start,end){const a=src.indexOf(start),b=src.indexOf(end,a);assert(a>=0&&b>a,`actual source slice ${start}`);return src.slice(a,b);}
const actualFns=[
 slice(bytes.c,'    function scopedPartLayersNow(z) {','    function scopedPartSelectorLayerIds('),
 slice(bytes.c,'    function scopedPartSelectorLayerIds(r) {','    function scopedPartAppearance('),
 slice(bytes.c,'    function scopedPartAppearance(z) {','    function scopedPartJson('),
 slice(bytes.c,'    function scopedPartJson(value) {','    function partOwnerCurrent('),
 slice(bytes.c,'    function partOwnerCurrent(z, key, provenance, sourceBinding) {','    function scopedPartProofCurrent('),
 slice(bytes.c,'    function scopedPartProofCurrent(z, key, part, provenance, sourceBinding) {','    function scopedPartProofMatches('),
 slice(bytes.c,'    function currentPartZoneOwners(parts, hits) {','    function registerAppliedPartZones('),
 slice(bytes.c,'    function partRegionKey(r) {','    function hasPriorPartIdentity(')
].join('\n');
function maskHash(mask){let h=2166136261;for(let i=0;i<mask.length;i++)h=Math.imul(h^(Number(mask[i])&255),16777619);return mask.length+':'+(h>>>0).toString(36);}
function fixture(mutator){
 const source={generation:7,path:'C:/car.psd',fingerprint:'file-sha256:'+'a'.repeat(64),width:2048,height:2048};
 const zoneMask=Uint8Array.from([1,0,1,1]),partMask=Uint8Array.from([1,0,1,1]);
 const layer={id:'paint-layer-id',name:'Car Paint',visible:true,locked:false,opacity:100};
 const z={id:'roof-owner-1',name:'AI green roof',regionMask:zoneMask,useRegion:true,muted:false,baseColorMode:'solid',baseColor:'#1f8a3b',base:'#gloss',finish:'f_gloss',baseColorStrength:1,baseStrength:1,specShiftR:0,specShiftG:0,specShiftB:0};
 const w={console,Uint8Array,Math,JSON,Array,Object,String,Number,isFinite,window:null,zones:[z],_psdLayers:[layer],_editReg:{},_editRegSig:null,
  CAR:{signature:()=> 'current-car-signature',layoutSig:()=> 'layout-7',maskFor:()=>({mask:partMask})},
  Z:{footprint:()=>({share_pct:2.9,visible_pct:2.9}),findLayer:()=>layer},
  SPBSourceLoadTransaction:{isCommitted:()=>true,getGeneration:()=>7,getCommittedGeneration:()=>7,getCommittedPath:()=>source.path,getCommittedFingerprint:()=>source.fingerprint,getCommittedKind:()=> 'layered'},
  getCurrentSourcePaintFile:()=>source.path,document:{getElementById:()=>({width:2048,height:2048})},
  zoneSourceLayerIds:()=>['paint-layer-id'],scopedPartSourceNow:()=>({...source}),carSig:()=> 'current-car-signature',
  scopedPartJson:null,scopedPartLayersNow:null,scopedPartSelectorLayerIds:null,scopedPartAppearance:null,
  _editRegSig:'current-car-signature'};w.window=w;w.SpbProElements={sig:()=>''};
 vm.createContext(w);vm.runInContext(actualFns+'\nthis.__editKey=editKey;this.__owners=currentPartZoneOwners;this.__partOwner=partOwnerCurrent;this.__proof=scopedPartProofCurrent;',w,{filename:'actual-owner-proof'});
 const region={island:'roof',layers:['Car Paint']};const key=w.__editKey(region);w._editReg[key]=z.name;
 const layers=w.scopedPartLayersNow(z);
 z._aiPartSource={...source};z._aiPartProv={r:JSON.stringify(region),z:maskHash(zoneMask),p:maskHash(partMask),l:'layout-7',e:'',s:{...source},car:'current-car-signature',layers:layers.ids,layerState:layers.states};
 if(mutator)mutator({w,z,layer,zoneMask,partMask,source,key});
 const hit={zone_id:z.id,zone:z.name,hex:z.baseColor,share:2.9,share_pct:2.9,selects_pct:2.9,finish:z.finish,layers:['Car Paint']};
 const proofs=w.__owners(['roof'],[hit]);
 return {w,z,hit,proofs,key,source,partOwner:w.__partOwner(z,key),proof:w.__proof(z,key,'roof')};
}
const design=(()=>{const w={console};w.window=w;vm.createContext(w);vm.runInContext(bytes.d,w);return w.SpbProDesign;})();
const E=(()=>{const w={console};w.window=w;vm.createContext(w);w.SpbProDesign=design;vm.runInContext(bytes.e,w);return w.SpbProEdit;})();
function compile(f,request='Make green on the roof blue'){
 const env={palette:[{hex:'#01ff00',name:'bright green',share_pct:28},{hex:'#1450b4',name:'blue',share_pct:3}],layers:[{name:'Car Paint',role:'body paint'}],zoneColours:f.hit?[f.hit]:[],currentPartZoneOwners:()=>f.proofs};
 const planned=E.plan(request,env),out=E.compile(planned,env);return {planned,out};
}
const rows=[];
// Main acceptance is actual currentPartZoneOwners -> actual E plan/compile.
const base=fixture(),good=compile(base);if(base.proofs.length!==1)console.error('PROOFDEBUG',JSON.stringify({partOwner:base.partOwner,proof:base.proof,region:base.z._aiPartProv,key:base.key},null,2));assert.equal(base.proofs.length,1);if(good.out.zones.length!==1)console.error('DEBUG',JSON.stringify({planned:good.planned,out:good.out,proof:base.proofs},null,2));assert.equal(good.out.zones.length,1);assert(good.out.zones[0]._meta.zoneEdit);assert.equal(good.out.zones[0]._meta.zoneEdit.zone_id,base.z.id);assert.equal(String(good.out.zones[0].color).toLowerCase(),'#1450b4');assert.equal(good.out.zones[0].finish,undefined);rows.push({id:'current-owner-with-source-green-conflict',pass:true,owner:base.proofs[0].zone_id,zoneEdit:good.out.zones[0]._meta.zoneEdit,finishPreservedByOmission:true});
const finish=compile(base,'Make green on the roof chrome');assert.equal(finish.out.zones.length,1);assert.equal(finish.out.zones[0]._meta.zoneEdit.zone_id,base.z.id);rows.push({id:'finish-followup-targets-same-owner',pass:true,owner:finish.out.zones[0]._meta.zoneEdit.zone_id});
const invalid=[
 ['edited-mask',({zoneMask})=>{zoneMask[1]=1;}],
 ['changed-layout',({w})=>{w.CAR.layoutSig=()=> 'layout-changed';}],
 ['changed-source',({source,w})=>{source.generation=8;w.scopedPartSourceNow=()=>({...source});}],
 ['hidden-layer',({layer})=>{layer.visible=false;}],
 ['muted-owner',({z})=>{z.muted=true;}],
 ['duplicate-id',({w,z})=>{w.zones.push({...z,name:'Duplicate id'});}],
 ['changed-solid-strength',({z})=>{z.baseColorStrength=.7;},'compiler-refusal'],
 ['non-solid',({z})=>{z.baseColorMode='gradient';},'compiler-refusal'],
 ['invisible-footprint',({w})=>{w.Z.footprint=()=>({share_pct:2.9,visible_pct:0});}],
 ['partial-selector',({z})=>{z._aiPartProv.r=JSON.stringify({island:'roof',layers:['Car Paint'],portion:'upper'});}],
 ['bad-layer-selector',({z})=>{z._aiPartProv.r=JSON.stringify({island:'roof',layers:['Missing Layer']});}]
];
for(const [id,mutate,mode] of invalid){const f=fixture(mutate);if(mode==='compiler-refusal')assert.equal(f.proofs.length,1,id+' has structurally current proof but non-default appearance');else assert.equal(f.proofs.length,0,id+' should fail actual controller proof');const result=compile(f);assert.equal(result.out.zones.length,0,id+' must not compile a color-zone edit');assert(result.out.ask,id+' should ask/refuse');rows.push({id,pass:true,controllerProofs:f.proofs.length,compiledZones:result.out.zones.length,asked:!!result.out.ask});}
const mismatchedHit=fixture();mismatchedHit.hit.hex='#007700';const mismatchedCompile=compile(mismatchedHit);assert.equal(mismatchedCompile.out.zones.length,0);assert(mismatchedCompile.out.ask);rows.push({id:'hit-color-mismatch-with-current-proof',pass:true,controllerProofs:mismatchedHit.proofs.length,compiledZones:0,asked:true});
const sourceOnly=fixture();sourceOnly.w.zones.length=0;sourceOnly.proofs=[];sourceOnly.hit=null;const sourceControl=compile(sourceOnly);assert.equal(sourceControl.out.zones.length,1);assert(!sourceControl.out.zones[0]._meta.partZoneProof);rows.push({id:'no-owner-source-color-control',pass:true,compiledZones:sourceControl.out.zones.length,selector:sourceControl.out.zones[0].region});
const report={work_item:'W93 independent actual-owner proof review of W89 candidate',date:'2026-10-04',status:'PASS_WITH_LIMITS',oracle:{path:oraclePath,sha256:pins.oracle,cases:oracle.case_count,frozenBeforeInspection:true},sources:{controller:{path:cpath,sha256:hash(Buffer.from(bytes.c))},edit:{path:epath,sha256:hash(Buffer.from(bytes.e))},design:{path:dpath,sha256:hash(Buffer.from(bytes.d))}},counts:{freshCases:rows.length,passed:rows.length,failed:0,providers:0,native:0},rows,limits:['Actual candidate controller functions partOwnerCurrent(), scopedPartProofCurrent() and currentPartZoneOwners() execute with real source/zone/layer/mask state fields; controlled CAR, transaction, layer lookup, and footprint readers provide deterministic fixtures.','Actual candidate E.plan()/E.compile() consume the real proof callback. Rendering, native UI, queued apply, saved artifact roundtrip, and runtime installation are not exercised.','No provider, browser, native paint, server, or live source calls.']};
const out=path.join(root,'docs/handoff_reports/AI_HELPER_14H_OWNED_SCOPED_COLOUR_W93_REVIEW_2026-10-04.json');fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
