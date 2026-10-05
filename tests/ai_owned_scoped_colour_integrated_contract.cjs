'use strict';
// W40 replays the W35 frozen desired-behaviour oracle; no W35 artifacts are overwritten.
const ORACLE = {
  frozenAt: '2026-10-04 before W40 candidate construction/inspection',
  candidateGlob: '_easy_claude_work/ai14h_w40_candidate/**',
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
const candidate = path.join(root, '_easy_claude_work/ai14h_generation3_runtime1/js');
const sources = {
  ai: fs.readFileSync(path.join(candidate, 'spb-pro-ai.js'), 'utf8'),
  edit: fs.readFileSync(path.join(candidate, 'spb-pro-edit.js'), 'utf8'),
  design: fs.readFileSync(path.join(candidate, 'spb-pro-design.js'), 'utf8'),
  kit: fs.readFileSync(path.join(candidate, 'spb-pro-zone-kit.js'), 'utf8')
};
const HASHES = {"spb-pro-ai.js": "3DA5C98B7202288979EFE0F53FE48818F31A6A5B5428BFB178CAEBA5C25E82D6", "spb-pro-edit.js": "19CBB899006D625BD2649FDAF8903EDA48D6BF8D9BD22BE0D90DB7C52673937E", "spb-pro-zone-kit.js": "EA9E169B909A30A6431F7FD48B87658B8258D480F165D304CB0CA5DAC8983AF7", "spb-ai-operation.js": "47587A1A53A35CE7E58825BAC864BD75C2421D26C19791957F57BB199A7000C6", "spb-ai-lease.js": "DE276372A763310EC051DB141FCB1D601E11DBF193843E2B21A405226F782134", "spb-ai-part-memory.js": "6E0D1E1466FECA847D3A1C3300F32779BA610F3B6C72C7904A6C8FD97A6B3652", "spb-ai-part-memory-project.js": "763D36ADDCA501256E1346D58B797D339B15666D04273CBF5C4840B15C1C6FC1", "spb-ai-complete-instruction-guard.js": "BA0AF1F9E217695ED733DDE81C8DEC1A735DD1F052E8C06B3098866D392A551C", "spb-pro-design.js": "0533393FF5F2170236F60D4ED489C7AE52F98805E12B0764DA67A967F756F2E8"};
function hash(s) { return crypto.createHash('sha256').update(s).digest('hex').toUpperCase(); }
assert.equal(hash(sources.ai), HASHES['spb-pro-ai.js'], 'pinned W31 AI source');
assert.equal(hash(sources.edit), HASHES['spb-pro-edit.js'], 'pinned W31 edit planner source');
assert.equal(hash(sources.design), HASHES['spb-pro-design.js'], 'pinned W31 design source');
assert.equal(hash(sources.kit), HASHES['spb-pro-zone-kit.js'], 'pinned W40 part-provenance helper');
function slice(s, start, end) { const a=s.indexOf(start),b=s.indexOf(end,a+start.length);assert(a>=0&&b>a,`source boundaries: ${start}`);return s.slice(a,b); }
function maskHash(m) { let h=2166136261; for(let i=0;i<m.length;i++)h=Math.imul(h^(Number(m[i])&255),16777619);return m.length+':'+(h>>>0).toString(36); }
function makeWorld() {
  const zoneMask = new Uint8Array([255,0,255,0]), partMask = new Uint8Array([0,255,0,255]);
  const zone = { id:'roof-zone-1', name:'Roof Red', baseColorMode:'solid', baseColor:'#cc0000', base:'base::gloss',
    region:{island:'roof',layers:['body-layer']}, regionMask:zoneMask, useRegion:true, muted:false };
  const canvas = {width:2048,height:2048};
  const w = { console, Promise, Math, JSON, Object, Array, String, Number, RegExp, Date,
    zones:[zone], _editReg:{}, _editRegSig:'car-A', _editRegPendingBefore:{}, _gen:0,
    _psdLayers:[{id:'body-layer',name:'Body',role:'body paint',visible:true,locked:false,opacity:100}], sourceGeneration:11, sourceCommittedGeneration:11, sourceFingerprint:'fp-A', sourcePath:'paint.psd',
    layout:'layout-A', element:'element-A', writes:[], batchCalls:[], layerOpsCalls:0, committed:true,
    window:null, _psdPath:'paint.psd', G:name=>w[name],
    document:{getElementById:id=>id==='paintCanvas'?canvas:null},
    SPBSourceLoadTransaction:{isCommitted:()=>w.committed!==false,getGeneration:()=>w.sourceGeneration,getCommittedGeneration:()=>w.sourceCommittedGeneration,getCommittedPath:()=>w.sourcePath,getCommittedFingerprint:()=>w.sourceFingerprint},
    getCurrentSourcePaintFile:()=>w.sourcePath,
    SpbProCar:{signature:()=> 'car-A',layoutSig:()=>w.layout},
    CAR:{signature:()=> 'car-A',layoutSig:()=>w.layout,maskFor:()=>({mask:partMask})},
    Z:{findLayer:key=>w._psdLayers.filter(l=>String(l.id)===String(key)||String(l.name)===String(key))[0]||null,footprint:()=>({share_pct:10,visible_pct:10}),batch:(ops)=>{w.batchCalls.push(JSON.parse(JSON.stringify(ops)));return ops.map(op=>{const z=w.zones[op.zone];Object.assign(z,op.spec);w.writes.push({id:String(z.id),color:z.baseColor||z.color,finish:z.finish});return {ok:true,index:op.zone,name:z.name,applied:['color changed']};});}},
    SpbProElements:{sig:()=>w.element},
    zoneSourceLayerIds:z=>((z&&z.region&&z.region.layers)||[]).map(v=>{const l=w.Z.findLayer(v);return l&&l.id;}).filter(Boolean),
    undoSnapTake:()=>null, undoPushedSince:()=>[], zoneUndoStack:[], _layerUndoStack:[], zsnap:()=>({}), zoneIdx:id=>w.zones.findIndex(z=>String(z.id)===String(id)), applyLayerOps:()=>{w.layerOpsCalls++;return {lines:[],failed:[],undoSteps:0};},
    partRegistryState:()=>({}), registerAppliedPartZones:()=>{}, reconcilePartRegistry:()=>{}, clearPartRegistryPending:()=>{},
    renderZones:()=>{},triggerPreviewRender:()=>{}, paintPx:()=>null, friendlyZoneError:e=>String(e),
    normaliseSpec:s=>s,protectDecals:()=>null, editFn:null
  };
  w.window=w;
  vm.createContext(w);
  vm.runInContext(slice(sources.kit,'function regionMaskHash(mask)','function excludedUnion('),w,{filename:'actual-w40-part-provenance-slice.js'});
  vm.runInContext(sources.design,w,{filename:'candidate-spb-pro-design.js'});
  vm.runInContext(sources.edit,w,{filename:'candidate-spb-pro-edit.js'});
  vm.runInContext(slice(sources.ai,'function carSig()','function memNotes()')+
    slice(sources.ai,'function zoneLayerNames(z)','function editPlural(label)')+
    slice(sources.ai,'function markPartFollowupQueue(queue)','function registerAppliedPartZones(ops, results)')+
    slice(sources.ai,'function partRegionKey(r)','function elemKey(kind, info)')+
    slice(sources.ai,'function applyQueue(queue, label, noUndo, elementIdentity)','function mergePartRegistryUndo(current, next)'),
    w,{filename:'actual-w31-ownership-queue-apply-slices.js'});
  const key=w.editKey(zone.region);
  // Actual ZoneKit helper records validated source, car, selector and layer snapshots.
  w.rememberPartRegion(zone,zone.region,partMask); w._editReg[key]=zone.name;
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
function queueOnlyActual(w, compiled) {
  const opQueue=[];
  const editFn=args=>{const idx=w.zones.findIndex(z=>String(z.id)===String(args.zone_id));if(idx<0)return {error:'gone'};const spec={};if(args.color!=null)spec.baseColor=args.color;if(args.finish!=null)spec.finish=args.finish;if(args.spec_shift!=null){spec.specShiftR=args.spec_shift.metal;spec.specShiftG=args.spec_shift.rough;spec.specShiftB=args.spec_shift.clearcoat;}opQueue.push({kind:'edit',zone:idx,spec,_spbPartRegKey:args._spbPartRegKey,_spbPartOwnerName:args._spbPartOwnerName,_spbScopedPartProof:args._spbScopedPartProof});return {ok:true};};
  const addFn=()=>({error:'unexpected add'});
  const queued=w.queueEditZones(compiled,addFn,editFn);
  return {queued,opQueue};
}
function queueAndApplyActual(w, compiled) {
  const {queued,opQueue}=queueOnlyActual(w,compiled);
  const applied=w.applyQueue(opQueue,'W40 repair review',false);
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
scenario('source-generation-change-after-compile',({w})=>{w.sourceGeneration++;w.sourceCommittedGeneration++;},'reject after committed source generation advances');
scenario('same-path-replacement-after-compile',({w})=>{w.sourceFingerprint='fp-B';w.sourceGeneration++;w.sourceCommittedGeneration++;},'reject after same-path source replacement');
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
const supplemental=[];
function applyBoundaryCase(id, mutation) {
  const {w}=makeWorld(), planned=compile(w), queued=queueOnlyActual(w,planned);
  assert.equal(queued.queued.errs.length,0,'supplemental fixture queues while proof is current');
  assert.equal(queued.opQueue.length,1,'supplemental fixture carries exactly one scoped edit');
  queued.opQueue.push({kind:'layer',layer:'body-layer',visible:false});
  mutation({w,ops:queued.opQueue});
  const applied=w.applyQueue(queued.opQueue,'W40 apply-time review',false);
  supplemental.push({id,queueLength:queued.opQueue.length,batchCalls:w.batchCalls.length,layerOpsCalls:w.layerOpsCalls,zoneColor:w.zones[0].baseColor,
    finish:w.zones[0].base,failed:applied.failed||[],verdict:(w.batchCalls.length===0&&w.layerOpsCalls===0&&w.zones[0].baseColor==='#cc0000')?'pass':'fail'});
}
applyBoundaryCase('apply-time-source-generation-race-cancels-whole-queue',({w})=>{w.sourceGeneration++;w.sourceFingerprint='fp-after-queue';});
applyBoundaryCase('apply-time-manual-layer-restriction-cancels-whole-queue',({w})=>{w._psdLayers[0].visible=false;});
applyBoundaryCase('apply-time-malformed-proof-cancels-whole-queue',({ops})=>{ops[0]._spbScopedPartProof.source.fingerprint='';});
{
  const {w,zone,partMask}=makeWorld(); w._psdLayers[0].name='Car Paint'; zone.region.layers=['Car Paint'];
  w.rememberPartRegion(zone,zone.region,partMask); const key=w.editKey(zone.region); w._editReg[key]=zone.name;
  const hits=w.SpbProEdit.prepZoneColours(w.zoneColours()), proof=w.currentPartZoneOwners(['roof'],hits);
  const result=w.SpbProEdit.compileRequest({target:'red',part:'roof',colour:'#00ff00'}, {palette:[],layers:[{name:'Car Paint',role:'body paint',hidden:false}],zoneColours:w.zoneColours(),currentPartZoneOwners:w.currentPartZoneOwners});
  supplemental.push({id:'native-Car-Paint-name-resolves-to-live-layer-UUID',currentOwners:proof.length,compiledZones:result.zones.length,asked:!!result.ask,
    zoneLayerIds:w.zoneSourceLayerIds(zone),regionLayerNames:zone.region.layers,verdict:(proof.length===1&&result.zones.length===1&&!result.ask)?'pass':'fail'});
}
{
  const {w,zone,key}=makeWorld(), current=zone._aiPartProv;
  const legacy={r:current.r,z:current.z,p:current.p,l:current.l,e:current.e};
  const hydrated=Object.assign({},legacy,{s:zone._aiPartSource,car:'car-A',layers:['body-layer'],layerState:[{id:'body-layer',visible:true,locked:false,opacity:100}]});
  const proof=w.scopedPartProofCurrent(zone,key,'roof',hydrated,zone._aiPartSource);
  supplemental.push({id:'fresh-restored-provenance-can-be-supplied-without-zone-mutation',proof:!!proof,zoneProvenanceUnchanged:zone._aiPartProv===current,
    verdict:(!!proof&&zone._aiPartProv===current)?'pass':'fail',legacyHasFiveFields:Object.keys(legacy).length===5});
}
{
  const {w,zone}=makeWorld(); delete w.SPBSourceLoadTransaction.isCommitted;
  const hits=w.SpbProEdit.prepZoneColours(w.zoneColours()), rejected=w.currentPartZoneOwners(['roof'],hits);
  const result=w.SpbProEdit.compileRequest({target:'red',part:'roof',colour:'#00ff00'}, {palette:[],layers:[],zoneColours:w.zoneColours(),currentPartZoneOwners:w.currentPartZoneOwners});
  supplemental.push({id:'missing-committed-source-api-fails-closed-before-planning',currentOwners:rejected.length,compiledZones:result.zones.length,asked:!!result.ask,zoneColor:zone.baseColor,
    verdict:(rejected.length===0&&result.zones.length===0&&!!result.ask&&zone.baseColor==='#cc0000')?'pass':'fail'});
}
const reportPath=path.join(root,'docs/handoff_reports/AI_HELPER_14H_OWNED_SCOPED_COLOUR_INTEGRATED_2026-10-04.json');
const fail=cases.filter(x=>x.verdict==='fail');
const report={status:fail.length||supplemental.some(x=>x.verdict==='fail')?'FINDINGS':'PASS_WITH_LIMITS',task:'W40 isolated W31 scoped-colour compile-queue-apply repair replay',oracle:ORACLE,
 sources:{
  spbProAi:{path:'_easy_claude_work/ai14h_generation3_runtime1/js/spb-pro-ai.js',sha256:hash(sources.ai),baseW31Sha256:'C5C68D2BA9D81411DF712E55A097345EEE603F5D65F552C2E89E058D54182E99',bytes:Buffer.byteLength(sources.ai),pinnedCopy:'%TEMP%/spb_w40_source_pin/spb-pro-ai.js'},
  spbProEdit:{path:'_easy_claude_work/ai14h_generation3_runtime1/js/spb-pro-edit.js',sha256:hash(sources.edit),baseW31Sha256:'BB265B823056AF036F35376C8389728176513E3F332201E5FCA35825D6C2B274',bytes:Buffer.byteLength(sources.edit),pinnedCopy:'%TEMP%/spb_w40_source_pin/spb-pro-edit.js'},
  spbProDesign:{path:'_easy_claude_work/ai14h_generation3_runtime1/js/spb-pro-design.js',sha256:hash(sources.design),baseW31Sha256:'0533393FF5F2170236F60D4ED489C7AE52F98805E12B0764DA67A967F756F2E8',bytes:Buffer.byteLength(sources.design),pinnedCopy:'%TEMP%/spb_w40_source_pin/spb-pro-design.js'},
  spbProZoneKit:{path:'_easy_claude_work/ai14h_generation3_runtime1/js/spb-pro-zone-kit.js',sha256:hash(sources.kit),baseSha256:'6968963FC8D382E3ECDA629089A71A73A519270C0B577E98DF03D9F7D48D68D0',bytes:Buffer.byteLength(sources.kit),pinnedCopy:'%TEMP%/spb_w40_source_pin/spb-pro-zone-kit.js'}},
 history:{w35Baseline:{test:'tests/ai_owned_scoped_colour_review_contract.cjs',testSha256:'4E1FAB941B4C376752A44412D4EE9666B97C73E6207CD7D701BE517044E395EE',report:'docs/handoff_reports/AI_HELPER_14H_OWNED_SCOPED_COLOUR_REVIEW_2026-10-03.json',reportSha256:'1334C1CA216A37B48A00AF6FD9F3C1447313338CA24F88496E6A918D88F29350',result:'1 pass / 11 fail; preserved unchanged',freshCredit:false},w27HistoricalBaseline:{report:'W35 report replay subsection; W27 prior oracle remains historical and not re-run for W40',freshCredit:false},preFixLayerNameProbe:{aiSha256:'78A6C7528D8BD95DCE1B35CE5004A9F4B85A396BE596E3C9473ACDCA27D73564',zoneKitSha256:'EA9E169B909A30A6431F7FD48B87658B8258D480F165D304CB0CA5DAC8983AF7',result:'new Car Paint name-to-layer UUID positive fixture failed before selector resolution repair'},w23HistoricalBaseline:{report:'docs/handoff_reports/AI_HELPER_14H_CURRENT_ZONE_COLOUR_SCOPE_REVIEW_2026-10-03.json',reportSha256:'daf2060420db29468bda205d5da12e882bd59f84ea495e208270493b780744d1',sourceEditSha256:'868e698dd0dc6a3424d5bcb2612bc0f8f21dc7c6ca3ffa6ea2524193cd76078e',noRewrite:true,freshCredit:false}},
 reproduction:{script:'_easy_claude_work/ai14h_w40_candidate/reproduce_w40_patch.ps1',scriptSha256:hash(fs.readFileSync(path.join(root,'_easy_claude_work/ai14h_w40_candidate/reproduce_w40_patch.ps1'),'utf8')),patch:'_easy_claude_work/ai14h_w40_candidate/W40_REPAIR.patch',patchSha256:hash(fs.readFileSync(path.join(root,'_easy_claude_work/ai14h_w40_candidate/W40_REPAIR.patch'),'utf8')),scriptChecksPinnedW31AndW40Hashes:true,defaultDoesNotApply:true,applyToIsExplicitAndHunkChecked:true,smokeApply:{destination:'_easy_claude_work/ai14h_w40_candidate/smoke_apply_1',aiSha256:'83795ACDEF46EAE8F325593FC051E7D096F68E00EFE501B63A2EE3630F8A9C65',zoneKitSha256:'EA9E169B909A30A6431F7FD48B87658B8258D480F165D304CB0CA5DAC8983AF7',matchesCandidate:true}},
 verifiedContracts:['A positive owner requires exact persisted per-zone _aiPartSource equal to a current committed SourceLoadTransaction descriptor; transaction APIs must be present, isCommitted true, and committed generation equal to live generation.', 'The source descriptor binds normalized current path, committed fingerprint, generation and actual paintCanvas dimensions. CAR signature alone is not treated as source identity.', 'CAR geometry/layout, element signature, zone mask and CAR part mask are freshly checked; current visible/selected footprint must be positive.', 'Current zone ID and selector owner must be unique across all zones, including muted duplicates; owner must be active, registered, exact-part and still have the same color/material state captured at compile.', 'Actual zoneSourceLayerIds must match provenance layer IDs and layer state. Region layer names are resolved by exact unique Z.findLayer lookup to actual layer IDs; no role/name inference is used.', 'Compile proof equality is checked before queue callbacks; proof crosses doEdit into the actual edit queue; applyQueue validates again before generation increment, layer application, mask changes or Z.batch, refusing the whole mixed queue on any stale scoped proof.', 'Optional hydrated provenance/source arguments are accepted by proof helpers without mutating the live zone object.'],
 counts:{frozenW35Cases:cases.length,pass:cases.length-fail.length,fail:fail.length,supplementalCases:supplemental.length,supplementalPass:supplemental.filter(x=>x.verdict==='pass').length,supplementalFail:supplemental.filter(x=>x.verdict==='fail').length,queueOrApplyNoops:cases.filter(x=>x.verdict==='pass'&&x.queueOps===0).length,mockedBatchCalls:cases.reduce((n,x)=>n+x.applyBatches,0),providers:0,nativeCalls:0},cases,supplemental,
 findings:[],
 recommendation:'Merge only through a targeted patch against the frozen W31 hooks: preserve the compiler’s color-only spec, bind per-zone source identity at rememberPartRegion, verify exact current zone/car/layout/element/mask/layer/footprint/appearance state at plan→queue and queue→apply boundaries, and carry the non-decorative proof through doEdit. Keep a whole-queue refusal before layer/mask/zone effects if any scoped proof differs.',
 integrationPrerequisites:['Live SPBSourceLoadTransaction must expose isCommitted() === true and getCommittedGeneration() equal to getGeneration(); the current W40 VM mocks these fields, but the parent reports the live adapter is preparing them. Until present, W40 intentionally refuses scoped edits.', 'Runtime must load the patched spb-pro-zone-kit.js rememberPartRegion so new or freshly validated restored owners store _aiPartSource and layer bindings. No source-loader, serializer, project, renderer, or full native integration is included here.', 'Region selector layer names are resolved through the actual Z.findLayer and compared as unique layer IDs to zoneSourceLayerIds; this was added after a frozen Car Paint-name positive probe failed against direct name/UUID comparison.'],
 limits:['Actual W31/W40 spb-pro-ai proof/queue/apply helpers, actual SpbProEdit.compileRequest, and actual ZoneKit rememberPartRegion body were executed in a VM assembled from bounded source slices; spb-pro-edit and spb-pro-design are byte-identical W31 sources.', 'The twelve-case W35 desired oracle is unchanged and replayed; six W40 boundary/adapter/native-layer cases are separately labeled supplemental and not fresh W35 credit.', 'Z.batch, editFn, SourceLoadTransaction, CAR/Z masks/footprints, and the canvas are controlled test doubles. No native renderer, live UI, provider, project file, browser, MCP, mirror, or Wiki was invoked.', 'The candidate is isolated under _easy_claude_work and was not copied to live js/ files; source pins are external to the repo under TEMP.']};
fs.writeFileSync(reportPath,JSON.stringify({status:report.status,task:'Gen3 actual integrated compile/queue/apply replay',oracle:ORACLE,counts:report.counts,cases,supplemental,sourceHashes:HASHES,providerCalls:0,limits:['Original W35 desired oracle and W40 six supplements replayed unchanged against actual integrated helpers.','Zone batch, geometry, canvas, source transaction and Undo snapshot are controlled VM services; this verifies proof propagation and rejection, not native output or Undo.','No live source, provider, mirror or native effects.']},null,2)+'\n');
console.log(JSON.stringify({status:report.status,counts:report.counts,failures:fail.map(x=>x.id),report:reportPath},null,2));
