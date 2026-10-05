'use strict';
// W35 independent oracle. These expectations were frozen before inspecting W31
// candidate source. Cases concern source ownership and exact scoped-colour edits.
const ORACLE = {
  frozenAt: '2026-10-04 before W31 candidate inspection',
  candidateGlob: '_easy_claude_work/ai14h_w31_candidate/**',
  cases: [
    { id:'exact-island-roof-colour-only-retains-existing-finish-and-mask', invariant:'a current unique owner for the named island roof is edited by colour only; finish and region-mask identity remain unchanged' },
    { id:'forged-uuid-clone-is-not-owner', invariant:'a copied UUID or cloned descriptor cannot establish current ownership without current owner proof' },
    { id:'source-generation-change-after-compile', invariant:'a source reload after plan compilation prevents queue publication and application' },
    { id:'same-path-replacement-after-compile', invariant:'same-path committed-image replacement invalidates a previously compiled operation' },
    { id:'manual-mask-edit-after-compile', invariant:'manual mask revision after compile wins and scoped queue is rejected' },
    { id:'layout-change-after-compile', invariant:'layout/part geometry change after compile invalidates exact-part ownership' },
    { id:'element-ownership-change-after-compile', invariant:'numbers/sponsor/element owner change after compile invalidates the action' },
    { id:'layer-restriction-change-after-compile', invariant:'layer visibility/restriction change after compile prevents broader color application' },
    { id:'renamed-owner-revalidated-currently', invariant:'renaming the exact owner cannot silently redirect the compiled edit to a different zone' },
    { id:'duplicate-uuid-owner-ambiguity', invariant:'multiple current zones claiming one owner identity fail closed' },
    { id:'muted-zone-not-current-owner', invariant:'a muted zone does not qualify as the sole current owner of the target region' },
    { id:'shared-body-owner-does-not-satisfy-exact-part', invariant:'a broad body/shared owner cannot authorize an exact named-part colour edit' }
  ]
};

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const candidate = path.join(root, '_easy_claude_work/ai14h_w31_candidate/js');
const sources = {
  ai: fs.readFileSync(path.join(candidate, 'spb-pro-ai.js'), 'utf8'),
  edit: fs.readFileSync(path.join(candidate, 'spb-pro-edit.js'), 'utf8'),
  design: fs.readFileSync(path.join(candidate, 'spb-pro-design.js'), 'utf8')
};
const HASHES = {
  'spb-pro-ai.js':'C5C68D2BA9D81411DF712E55A097345EEE603F5D65F552C2E89E058D54182E99',
  'spb-pro-edit.js':'BB265B823056AF036F35376C8389728176513E3F332201E5FCA35825D6C2B274',
  'spb-pro-design.js':'0533393FF5F2170236F60D4ED489C7AE52F98805E12B0764DA67A967F756F2E8'
};
function hash(s) { return crypto.createHash('sha256').update(s).digest('hex').toUpperCase(); }
assert.equal(hash(sources.ai), HASHES['spb-pro-ai.js'], 'pinned W31 AI source');
assert.equal(hash(sources.edit), HASHES['spb-pro-edit.js'], 'pinned W31 edit planner source');
assert.equal(hash(sources.design), HASHES['spb-pro-design.js'], 'pinned W31 design source');
function slice(s, start, end) { const a=s.indexOf(start),b=s.indexOf(end,a+start.length);assert(a>=0&&b>a,`source boundaries: ${start}`);return s.slice(a,b); }
function maskHash(m) { let h=2166136261; for(let i=0;i<m.length;i++)h=Math.imul(h^(Number(m[i])&255),16777619);return m.length+':'+(h>>>0).toString(36); }
function makeWorld() {
  const zoneMask = new Uint8Array([255,0,255,0]), partMask = new Uint8Array([0,255,0,255]);
  const zone = { id:'roof-zone-1', name:'Roof Red', baseColorMode:'solid', baseColor:'#cc0000', base:'base::gloss',
    region:{island:'roof'}, regionMask:zoneMask, useRegion:true, muted:false };
  const w = { console, Promise, Math, JSON, Object, Array, String, Number, RegExp, Date,
    zones:[zone], _editReg:{}, _editRegSig:'car-A', _editRegPendingBefore:{}, _gen:0,
    _psdLayers:[{id:'body-layer',name:'Body',role:'body paint',visible:true}], sourceGeneration:11, sourceFingerprint:'fp-A',
    layout:'layout-A', element:'element-A', writes:[], batchCalls:[],
    window:null,
    CAR:{signature:()=> 'car-A',layoutSig:()=>w.layout,maskFor:()=>({mask:partMask})},
    Z:{footprint:()=>({share_pct:10,visible_pct:10}),batch:(ops)=>{w.batchCalls.push(JSON.parse(JSON.stringify(ops)));return ops.map(op=>{const z=w.zones[op.zone];Object.assign(z,op.spec);w.writes.push({id:String(z.id),color:z.baseColor||z.color,finish:z.finish});return {ok:true,index:op.zone,name:z.name,applied:['color changed']};});}},
    SpbProElements:{sig:()=>w.element},
    zoneSourceLayerIds:()=>['body-layer'],
    zsnap:()=>({}), zoneIdx:id=>w.zones.findIndex(z=>String(z.id)===String(id)), applyLayerOps:()=>({lines:[],failed:[],undoSteps:0}),
    partRegistryState:()=>({}), registerAppliedPartZones:()=>{}, reconcilePartRegistry:()=>{}, clearPartRegistryPending:()=>{},
    renderZones:()=>{},triggerPreviewRender:()=>{}, paintPx:()=>null, friendlyZoneError:e=>String(e),
    normaliseSpec:s=>s,protectDecals:()=>null, editFn:null
  };
  w.window=w;
  vm.createContext(w);
  vm.runInContext(sources.design,w,{filename:'candidate-spb-pro-design.js'});
  vm.runInContext(sources.edit,w,{filename:'candidate-spb-pro-edit.js'});
  vm.runInContext(slice(sources.ai,'function carSig()','function memNotes()')+
    slice(sources.ai,'function zoneLayerNames(z)','function editPlural(label)')+
    slice(sources.ai,'function markPartFollowupQueue(queue)','function registerAppliedPartZones(ops, results)')+
    slice(sources.ai,'function partRegionKey(r)','function elemKey(kind, info)')+
    slice(sources.ai,'function applyQueue(queue, label, noUndo, elementIdentity)','function partRegHas(obj, key)'),
    w,{filename:'actual-w31-ownership-queue-apply-slices.js'});
  const key=w.editKey({island:'roof'}), p={r:JSON.stringify({island:'roof'}),z:maskHash(zoneMask),p:maskHash(partMask),l:w.layout,e:w.element};
  zone._aiPartProv=p; w._editReg[key]=zone.name;
  return {w,zone,key,zoneMask,partMask};
}
function compile(w, overrides) {
  const hits=w.zoneColours();
  const env={palette:[],layers:w._psdLayers.map(l=>({name:l.name,role:l.role,hidden:!l.visible})),zoneColours:hits,currentPartZoneOwners:w.currentPartZoneOwners};
  const result=w.SpbProEdit.compileRequest(Object.assign({target:'red',part:'roof',colour:'#00ff00'},overrides||{}),env);
  assert.equal(result.ask,null,'the current verified exact-part scenario compiles without clarification');
  assert.equal(result.zones.length,1);
  return result;
}
function queueAndApplyActual(w, compiled) {
  const opQueue=[];
  const editFn=args=>{const idx=w.zones.findIndex(z=>String(z.id)===String(args.zone_id));if(idx<0)return {error:'gone'};const spec={};if(args.color!=null)spec.baseColor=args.color;if(args.finish!=null)spec.finish=args.finish;opQueue.push({kind:'edit',zone:idx,spec});return {ok:true};};
  const addFn=()=>({error:'unexpected add'});
  const queued=w.queueEditZones(compiled,addFn,editFn);
  const applied=w.applyQueue(opQueue,'W35 review',false);
  return {queued,opQueue,applied};
}
const cases=[];
function scenario(id, mutate, expectation, overrides) {
  const {w,zone,zoneMask}=makeWorld(), planned=compile(w,overrides), initialProof=w.currentPartZoneOwners(['roof'],w.SpbProEdit.prepZoneColours(w.zoneColours()));
  assert.equal(initialProof.length,1,'the frozen start fixture is one verified owner');
  if(mutate)mutate({w,zone});
  const postProof=w.currentPartZoneOwners(['roof'],w.SpbProEdit.prepZoneColours(w.zoneColours()));
  const out=queueAndApplyActual(w,planned);
  cases.push({id,expected:expectation,proofsAfterMutation:postProof.length,queueOps:out.opQueue.length,applyBatches:w.batchCalls.length,writes:w.writes.slice(),zoneColor:zone.baseColor,base:zone.base,finish:zone.finish,maskSame:zone.regionMask===zoneMask});
}
// Fresh exact-owner control: colour-only edits preserve existing finish and mask.
scenario('exact-island-roof-colour-only-retains-existing-finish-and-mask',null,'apply colour to the unique live owner while preserving finish and mask identity');
// Stale validations: each mutation happens after the actual planner has emitted zoneEdit metadata.
scenario('forged-uuid-clone-is-not-owner',({w,zone})=>{w.zones.push(Object.assign({},zone,{id:'forged-clone',regionMask:new Uint8Array(zone.regionMask),_aiPartProv:Object.assign({},zone._aiPartProv)}));},'reject stale proof when a same-selector clone appears');
scenario('source-generation-change-after-compile',({w})=>{w.sourceGeneration++;},'reject after committed source generation advances');
scenario('same-path-replacement-after-compile',({w})=>{w.sourceFingerprint='fp-B';w.sourceGeneration++;},'reject after same-path source replacement');
scenario('manual-mask-edit-after-compile',({zone})=>{zone.regionMask[0]=0;},'reject after the owner mask is manually edited');
scenario('layout-change-after-compile',({w})=>{w.layout='layout-B';},'reject after part layout changes');
scenario('element-ownership-change-after-compile',({w})=>{w.element='element-B';},'reject after element map changes');
scenario('layer-restriction-change-after-compile',({w})=>{w._psdLayers[0].visible=false;},'revalidate layer visibility/restriction before queue/apply',{layer:'Body'});
scenario('renamed-owner-revalidated-currently',({w,zone})=>{zone.name='Roof Red Renamed';},'do not silently use stale proof/label after owner rename');
scenario('duplicate-uuid-owner-ambiguity',({w,zone})=>{w.zones.push(Object.assign({},zone,{name:'Clone with duplicate id',regionMask:new Uint8Array(zone.regionMask),_aiPartProv:Object.assign({},zone._aiPartProv)}));},'reject ambiguous duplicate-id targets');
scenario('muted-zone-not-current-owner',({zone})=>{zone.muted=true;},'reject muted zone as current owner');
scenario('shared-body-owner-does-not-satisfy-exact-part',({zone})=>{zone._aiPartProv.r=JSON.stringify({part:'body'});},'reject a broad/shared body selector for exact roof scope');
const expected = cases.map(x=>x.id);
assert.deepEqual(expected,ORACLE.cases.map(x=>x.id),'all 12 frozen cases executed');
const exact=cases[0]; exact.verdict=(exact.queueOps===1&&exact.applyBatches===1&&exact.zoneColor==='#00ff00'&&exact.base==='base::gloss'&&exact.maskSame)?'pass':'fail';
for(const c of cases.slice(1))c.verdict=(c.applyBatches===0&&c.queueOps===0)?'pass':'fail';
const reportPath=path.join(root,'docs/handoff_reports/AI_HELPER_14H_OWNED_SCOPED_COLOUR_REVIEW_2026-10-03.json');
const fail=cases.filter(x=>x.verdict==='fail');
const report={status:fail.length?'FINDINGS':'PASS_WITH_LIMITS',task:'W35 independent W31 scoped-colour queue/apply review',oracle:ORACLE,
 sources:{
  spbProAi:{path:'_easy_claude_work/ai14h_w31_candidate/js/spb-pro-ai.js',sha256:hash(sources.ai),bytes:Buffer.byteLength(sources.ai),pinnedCopy:'%TEMP%/spb_w35_review_source_pin/spb-pro-ai.js'},
  spbProEdit:{path:'_easy_claude_work/ai14h_w31_candidate/js/spb-pro-edit.js',sha256:hash(sources.edit),bytes:Buffer.byteLength(sources.edit),pinnedCopy:'%TEMP%/spb_w35_review_source_pin/spb-pro-edit.js'},
  spbProDesign:{path:'_easy_claude_work/ai14h_w31_candidate/js/spb-pro-design.js',sha256:hash(sources.design),bytes:Buffer.byteLength(sources.design),pinnedCopy:'%TEMP%/spb_w35_review_source_pin/spb-pro-design.js'}},
 replay:{path:'_easy_claude_work/ai14h_w31_candidate/w27_replay.json',pinnedBeforeProducerReplaySha256:'4F1355E8BD9791F1105F9026EB68EA4DCF6A7B12DCA0DA9B512CB72918758A4E',candidateAfterReplaySha256:'CA148C6F88F70E2E3E78E3C091A6405117BD63D304DE2423743CDEC3CEA38473',producer8:{test:'tests/ai_owned_scoped_colour_candidate_contract.cjs',sha256:'150A60AF62B44ABF286EE733FD4693CBE9AAA8B540EBA9FA602795AAB7A7BE96',result:'passed 8 scoped-proof cases; W27 oracle replayed',freshCredit:false},w23Baseline:{report:'docs/handoff_reports/AI_HELPER_14H_CURRENT_ZONE_COLOUR_SCOPE_REVIEW_2026-10-03.json',reportSha256:'daf2060420db29468bda205d5da12e882bd59f84ea495e208270493b780744d1',sourceEditSha256:'868e698dd0dc6a3424d5bcb2612bc0f8f21dc7c6ca3ffa6ea2524193cd76078e',noRewrite:true,freshCredit:false},separateFromFreshCredit:true,note:'The source JSON was pinned before producer replay; its current candidate-path hash advanced during the separately-run producer test, so both before-copy and after-replay hashes are recorded. W23 remains an untouched historical baseline (no rewrite, no fresh credit). No producer or W27 cases contribute to the 12 fresh W35 cases.'},
 counts:{freshCases:cases.length,pass:cases.length-fail.length,fail:fail.length,queueOrApplyNoops:cases.filter(x=>x.verdict==='pass'&&x.queueOps===0).length,mockedBatchCalls:cases.reduce((n,x)=>n+x.applyBatches,0),providers:0,nativeCalls:0},cases,
 findings:[
  {severity:'P1',id:'queue/apply-time-proof-drop',sourceRefs:[{file:'js/spb-pro-edit.js',lines:[806,818]},{file:'js/spb-pro-ai.js',lines:[537,571,1199,1221]}],detail:'The actual E.compileRequest output carries _meta.partZoneProof. Actual queueEditZones handles _meta.zoneEdit by resolving only zone_id, constructs a plain edit spec, and passes it to editFn; it drops partZoneProof and creates no _spbPartRegKey/_spbPartOwnerName. Actual applyQueue revalidates only queues carrying those registry fields, so the zoneColour edit reaches Z.batch without rechecking source/mask/layout/element/owner state.'},
  {severity:'P1',id:'provenance-does-not-bind-source-generation',sourceRefs:[{file:'js/spb-pro-ai.js',lines:[651,669]}],detail:'partOwnerCurrent checks zone-mask hash, CAR layout signature, element signature, part-mask hash, registry name and unique helper owner. It does not read source-load generation or committed source fingerprint. The source-replacement cases deliberately keep CAR.signature stable to isolate the missing proof dimension; candidate behavior is source-confirmed, while real CAR signature stability for same-path replacement was not tested.'},
  {severity:'P2',id:'owner-changes-after-plan',sourceRefs:[{file:'js/spb-pro-ai.js',lines:[651,669,1221]}],detail:'Renames, muted state, duplicate selectors and changed mask/layout/element proof are rejected by a fresh currentPartZoneOwners call but not rechecked by the zoneEdit queue/apply path. Duplicate zone_id causes queueEditZones to select the last matching zone.'}
 ],
 recommendation:'Carry the immutable owner proof from zoneColourOps into the edit queue as a dedicated precondition; immediately before enqueue, and again at applyQueue before Z.batch, re-resolve current unique zone id/name/UUID, active state, committed source generation/fingerprint, current CAR layout/part mask, zone mask hash, element signature and effective layer restriction. Reject without writing if any proof member differs; keep color-only edit spec free of region fields so finish/mask are preserved.',
 limits:['Actual spb-pro-design, spb-pro-edit compileRequest, spb-pro-ai zoneColours/currentPartZoneOwners/queueEditZones/applyQueue bodies were executed in a VM.', 'Z.batch and editFn are controlled effects that record and apply the actual compiled edit spec to a minimal zone object; no native renderer, project file, provider, browser, MCP or live app was invoked.', 'The source-pin copy is external to the repo under TEMP; project-owned deliverables are only this test and this report.', 'The W27 14-case replay report is historical and not fresh credit; no claim is made for the producer 8-case suite or runtime/native integration.']};
fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,counts:report.counts,failures:fail.map(x=>x.id),report:reportPath},null,2));
