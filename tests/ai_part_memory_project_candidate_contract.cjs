'use strict';
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const cand = path.join(root, '_easy_claude_work/ai14h_w38_candidate/candidate/js');
const cases = require(path.join(root, '_easy_claude_work/ai14h_w38_candidate/oracle/cases.json')).cases;
assert.equal(cases.length, 10, 'the pre-implementation oracle remains 10 cases');
const memory = require(path.join(cand, 'spb-ai-part-memory.js'));
const stateSource = fs.readFileSync(path.join(cand, 'paint-booth-2-state-zones.js'), 'utf8');
const bridgeSource = fs.readFileSync(path.join(cand, 'spb-ai-part-memory-project.js'), 'utf8');
const frozen = {
  'paint-booth-2-state-zones.js': 'E1EFA310757FBBDBF5EA5CB030DDC651BDAC1A6618A8388DA1535D00D8F3BC95',
  'spb-ai-part-memory.js': '6E0D1E1466FECA847D3A1C3300F32779BA610F3B6C72C7904A6C8FD97A6B3652',
  'spb-pro-ai.js': '609B8EC85228F15D2CC9B3AB82CD692EB2EA90D258CF5045FD36448AD3C46C6B'
};
for (const [name, expected] of Object.entries(frozen)) {
  const actual = crypto.createHash('sha256').update(fs.readFileSync(path.join(root, '_easy_claude_work/ai14h_w38_candidate/sources', name))).digest('hex').toUpperCase();
  assert.equal(actual, expected, `frozen source changed: ${name}`);
}
const getStart = stateSource.indexOf('function getConfig() {');
const getEnd = stateSource.indexOf('\nfunction getSessionConfig()', getStart);
const loadStart = stateSource.indexOf('function loadConfigFromObj(cfg) {');
const loadEnd = stateSource.indexOf('\n// SHOKK / templates: session round-trip', loadStart);
assert.ok(getStart >= 0 && getEnd > getStart && loadStart >= 0 && loadEnd > loadStart, 'extract exact live serializer functions');
const nodes = new Uint8Array([1, 0, 1, 1]);
const mask = new Uint8Array([1, 0, 1, 1]);
const region = { island: 'roof', layers: ['Car Paint'] };
const prov = { r: JSON.stringify(region), z: '4:abc', p: '4:abc', l: 'layout-1', e: '' };
const zone = { id: 'uuid-1', name: 'Roof helper', useRegion: true, regionMask: nodes, muted: false, _aiPartProv: prov };
let maskRequired = true, carMaskCalls = 0, current = { committed: true, path: 'C:/cars/car-a.tga', fingerprint: 'fp-a', width: 2, height: 2, generation: 4 };
const countOwners = () => 1;
function proofFor(z) {
  return {
    isCommittedSource: s => !!s.committed && s.generation > 0,
    sameSourcePath: (a,b) => a.toLowerCase() === b.toLowerCase(),
    editKey: r => JSON.stringify(r),
    partOwnerCurrent: (live,p,key,s) => live === z && key === JSON.stringify(region) && p.e === '' && !!s.committed,
    partMaskCurrent: (live,p,key,s) => { carMaskCalls++; return !!maskRequired && p.p === '4:abc' && !!s.committed; },
    countOwners
  };
}
const bridgeContext = { window: {}, module: { exports: {} }, globalThis: {} };
vm.runInNewContext(bridgeSource, bridgeContext);
const Project = bridgeContext.window.SpbAIPartMemoryProjectCandidate;
assert.ok(Project, 'candidate bridge loads');
let registered = [];
const api = Project.create(memory, {
  currentSource: () => current,
  saveProof: z => proofFor(z),
  restoreProof: z => proofFor(z),
  registerOwner: (z,key,p,s) => { registered.push({id:z.id,key,gen:s.generation}); return true; }
});
const sourceContext = {
  window: { SpbAIPartMemoryProjectCandidate: api, SPBSourceLayerLinks: { snapshotBindings: () => ({}) }, getCurrentSourcePaintFile: () => current.path },
  document: { getElementById: id => ({ value: id === 'outputDir' ? '' : '', checked: false }) },
  zones: [zone], _psdLayers: [], _savedMaskCanvasSize: () => ({w:2,h:2}), _savedMaskExpectedSize: () => ({w:2,h:2}),
  activeSpecChannel: 'all', _getActiveImportedSpecMapPath: () => '', _newZoneId: () => 'new-id', _encodeSavedMask: x => x ? {width:2,height:2,data:[...x]} : null,
  _decodeSavedMask: x => x && x.data ? new Uint8Array(x.data) : null, _cloneUint8ArrayLike: x => x,
  updateWearDisplay: () => {}, toggleNightBoostSlider: () => {}, updateOutputPath: () => {}, _sanitizeZonesInPlace: () => {}, renderZones: () => {}, renderZoneDetail: () => {},
  selectedZoneIndex: 0, nextLinkGroupId: 1
};
sourceContext.window.window = sourceContext.window;
vm.createContext(sourceContext);
vm.runInContext(stateSource.slice(getStart, getEnd) + '\nthis.__getConfig=getConfig;', sourceContext);
vm.runInContext(stateSource.slice(loadStart, loadEnd) + '\nthis.__loadConfig=loadConfigFromObj;', sourceContext);
const cfg = sourceContext.__getConfig();
assert.ok(cfg.zones[0].spbAIPartMemory && cfg.zones[0].spbAIPartMemory.schema === memory.schema, 'actual getConfig captures sanitized compact owner record');
assert.equal(JSON.stringify(cfg.zones[0].spbAIPartMemory).includes('generation'), false, 'persisted record excludes runtime generation');
sourceContext.zones = [];
sourceContext.__loadConfig(cfg);
assert.equal(sourceContext.zones[0]._aiPartProv, undefined, 'actual loadConfig does not grant ownership');
assert.ok(sourceContext.zones[0]._spbAIPartMemoryPending, 'actual loadConfig stages inert sanitized metadata');
maskRequired = true;
current = { ...current, generation: 9 };
let result = api.rebindAfterCommit(sourceContext.zones);
assert.deepEqual(JSON.parse(JSON.stringify(result)), {rebound:1,rejected:0}, 'same-content reopen rebinds under fresh proof and new generation');
assert.equal(sourceContext.zones[0]._aiPartProv.e, '', 'empty element signature is preserved exactly');
assert.equal(registered.at(-1).gen, 9, 'registry callback receives current, not persisted, generation');

function stagedFor(source=current) { const z = { ...sourceContext.zones[0], id:'uuid-1', name:'Roof helper', muted:false, useRegion:true, regionMask: nodes, _spbAIPartMemoryPending: cfg.zones[0].spbAIPartMemory }; current = source; return z; }
const saved = cfg.zones[0].spbAIPartMemory;
const rejects = [
  ['fingerprint', {...current,fingerprint:'changed'}], ['path',{...current,path:'C:/cars/car-b.tga'}], ['dimensions',{...current,width:3}]
];
for (const [label, source] of rejects) { const z=stagedFor(source); result=api.rebindAfterCommit([z]); assert.equal(result.rebound,0, label+' mismatch rejected'); assert.ok(z._spbAIPartMemoryPending, label+' mismatch stays inert'); }
current = {...current, committed:false, generation:10};
const pending = stagedFor(current); result=api.rebindAfterCommit([pending]); assert.equal(result.rebound,0,'uncommitted source never rebinds');
current = {...current, committed:true, generation:11};
const noMaskProof = Project.create(memory,{ currentSource:()=>current, saveProof:z=>proofFor(z), restoreProof:z=>({...proofFor(z),partMaskCurrent:()=>false}), registerOwner:()=>true });
const missingMask = stagedFor(current); assert.equal(noMaskProof.rebindAfterCommit([missingMask]).rebound,0,'missing CAR.maskFor proof rejects even when e is empty');
const missingElementSaved = JSON.parse(JSON.stringify(saved)); delete missingElementSaved.provenance.e;
assert.equal(memory.sanitizeRecord(missingElementSaved),null,'absent element signature rejects');
const nullElementSaved = JSON.parse(JSON.stringify(saved)); nullElementSaved.provenance.e=null;
assert.equal(memory.sanitizeRecord(nullElementSaved),null,'null element signature rejects');
const muted = stagedFor(current); muted.muted=true; assert.equal(api.rebindAfterCommit([muted]).rebound,0,'muted owner rejected by proof');
const dupe = stagedFor(current); const dupeProof = {...proofFor(dupe),countOwners:()=>2};
const dupeApi = Project.create(memory,{currentSource:()=>current,saveProof:()=>dupeProof,restoreProof:()=>dupeProof,registerOwner:()=>true});
assert.equal(dupeApi.rebindAfterCommit([dupe]).rebound,0,'duplicate owner rejected');
assert.equal(memory.sanitizeRecord({ ...saved, provenance: { ...saved.provenance, arbitraryPixels: [1,2] } }), null, 'extra pixel-like provenance key rejects');
// Exercise the production-shaped transaction + mandatory CAR.maskFor adapter.
function maskHash(m) { let h=2166136261; for (const v of m) h=Math.imul(h^(Number(v)&255),16777619); return m.length+':'+(h>>>0).toString(36); }
let committed = {...current, committed:true, generation:20}, runtimeZones=[], registeredRuntime=[];
const runtimeRegion={part:'roof',layers:['Car Paint']}, runtimeMask=new Uint8Array([1,0,1,1]);
const runtimeZone={id:'uuid-runtime',name:'Roof owner',useRegion:true,regionMask:runtimeMask,muted:false,
  _aiPartProv:{r:JSON.stringify(runtimeRegion),z:maskHash(runtimeMask),p:maskHash(runtimeMask),l:'layout-r',e:''}};
runtimeZones=[runtimeZone];
const runtime={
  transaction:{getCommittedPath:()=>committed.path,getCommittedFingerprint:()=>committed.fingerprint,getGeneration:()=>committed.generation},
  dimensions:()=>({width:committed.width,height:committed.height}),
  isCommitted:(p,f,g)=>committed.committed===true&&p===committed.path&&f===committed.fingerprint&&g===committed.generation,
  sameSourcePath:(a,b)=>a.toLowerCase()===b.toLowerCase(), editKey:r=>JSON.stringify(r),
  CAR:{maskFor:part=>part==='roof'?{mask:runtimeMask}:null}, hashMask:maskHash,
  partOwnerCurrent:(z,p,key,s)=>runtimeZones.includes(z)&&!z.muted&&z.useRegion===true&&p.l==='layout-r'&&p.e===''&&
    key===JSON.stringify(runtimeRegion)&&maskHash(z.regionMask)===p.z&&s.generation===committed.generation,
  countOwners:(key,id,candidate)=>runtimeZones.filter(z=>{
    const p=z===candidate?(z._aiPartProv||(z._spbAIPartMemoryPending&&z._spbAIPartMemoryPending.provenance)):z._aiPartProv;
    try{return !!p&&JSON.stringify(JSON.parse(p.r))===key;}catch(_){return false;}
  }).length,
  registerOwner:(z,key,p,s)=>{registeredRuntime.push({id:z.id,key,generation:s.generation});return true;}
};
const runtimeApi=Project.createRuntime(memory,runtime);
const runtimeSaved=runtimeApi.capture(runtimeZone);
assert.ok(runtimeSaved,'runtime adapter captures only committed current owner');
const runtimeLoaded={id:runtimeZone.id,name:runtimeZone.name,useRegion:true,regionMask:new Uint8Array(runtimeMask),muted:false};
assert.equal(runtimeApi.stage(runtimeLoaded,runtimeSaved),true,'runtime load stages record as inert metadata');
assert.equal(runtimeLoaded._aiPartProv,undefined,'staging never assigns provenance');
runtimeZones=[runtimeLoaded];
committed={...committed,generation:21};
const rebound=runtimeApi.rebindAfterCommit([runtimeLoaded]);
assert.deepEqual(JSON.parse(JSON.stringify(rebound)),{rebound:1,rejected:0});
assert.equal(registeredRuntime[0].generation,21,'restore binds to current transaction generation');
assert.equal(runtimeLoaded._aiPartProv.e,'','actual mask proof accepts a legitimate empty signature');
const noCarApi=Project.createRuntime(memory,{...runtime,CAR:null});
const noCarZone={...runtimeLoaded,id:'uuid-runtime-2',_aiPartProv:undefined,_spbAIPartMemoryPending:runtimeSaved};
assert.equal(noCarApi.rebindAfterCommit([noCarZone]).rebound,0,'missing CAR.maskFor fails closed');
console.log('PASS: actual getConfig/loadConfig staging, 10 frozen cases, current transaction and mandatory mask proof');










