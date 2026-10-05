// W31 isolated candidate proof for scoped current-zone colour edits.
// Candidate code and frozen inputs live under _easy_claude_work/ai14h_w31_*.
const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { execFileSync } = require('child_process');
const H = require('../_easy_claude_work/stack_h.js');
const ROOT = path.resolve(__dirname, '..');
const BASE = path.join(ROOT, '_easy_claude_work', 'ai14h_w31_sources', 'js');
const CAND = path.join(ROOT, '_easy_claude_work', 'ai14h_w31_candidate', 'js');
const cases = [
  {id:'W31-01',ask:'Change the blue on the roof to pale pink.',setup:'one registered helper-owned exact roof zone; current mask/layout/element match',oracle:'one same-UUID scoped zoneEdit'},
  {id:'W31-02',ask:'Change the blue on the roof to pale pink.',setup:'whole-body owner plus roof request',oracle:'clarify, no partial output'},
  {id:'W31-03',ask:'Change the blue on the roof to pale pink.',setup:'registered roof owner has an edited regionMask',oracle:'clarify'},
  {id:'W31-04',ask:'Change the blue on the roof to pale pink.',setup:'CAR.maskFor absent or returns no current mask',oracle:'clarify'},
  {id:'W31-05',ask:'Change the blue on the roof to pale pink.',setup:'two active helper owners match the part/color',oracle:'clarify ambiguity'},
  {id:'W31-06',ask:'Change the blue on the roof to pale pink.',setup:'muted or zero-footprint owner',oracle:'clarify'},
  {id:'W31-07',ask:'Change the blue on the roof to pale pink.',setup:'manual zone has matching name/color but no _aiPartProv/registry entry',oracle:'clarify, no adoption'},
  {id:'W31-08',ask:'Change the blue on the roof to pale pink.',setup:'part proof has stale layout or element signature',oracle:'clarify'}
];
const freshSha = 'd5e24e30ff726503bd27bf6fc7c33576491b6efc18093940438f8ff46d0743e5';
assert.strictEqual(crypto.createHash('sha256').update(JSON.stringify(cases)).digest('hex'), freshSha, 'W31 fresh case set changed');
const baselineReport = path.join(ROOT, 'docs', 'handoff_reports', 'AI_HELPER_14H_CURRENT_ZONE_COLOUR_SCOPE_REVIEW_2026-10-03.json');
const baselineReportSha = 'daf2060420db29468bda205d5da12e882bd59f84ea495e208270493b780744d1';
assert.strictEqual(crypto.createHash('sha256').update(fs.readFileSync(baselineReport)).digest('hex'), baselineReportSha, 'immutable W23 evidence changed');
const hashes = {
  'spb-pro-ai.js': '609b8ec85228f15d2cc9b3ab82cd692eb2ea90d258cf5045fd36448ad3c46c6b',
  'spb-pro-edit.js': 'd940e6688b3ed5e8fa0514c8774e73a4a2b564ad723e507166248e3e97ac75d0',
  'spb-pro-design.js': '0533393ff5f2170236f60d4ed489c7ae52f98805e12b0764da67a967f756f2e8'
};
function read(dir, name, expected) {
  const b = fs.readFileSync(path.join(dir, name));
  if (expected) assert.strictEqual(crypto.createHash('sha256').update(b).digest('hex'), expected, 'frozen source changed: ' + name);
  return b.toString('utf8');
}
const sources = Object.fromEntries(Object.keys(hashes).map(n => [n, read(BASE, n, hashes[n])]));
const candAi = read(CAND, 'spb-pro-ai.js'), candEdit = read(CAND, 'spb-pro-edit.js');
assert(candAi.includes('function currentPartZoneOwners(parts, hits)') && candAi.includes('currentPartZoneOwners: currentPartZoneOwners'), 'candidate proAI owner proof callback missing');
assert(candEdit.includes('env.currentPartZoneOwners(tg.parts, zh)'), 'candidate E compiler is not using proAI proof callback');
function extract(src, start, end) {
  const i=src.indexOf(start), j=src.indexOf(end,i);
  assert(i>=0 && j>i, 'could not extract actual helper '+start);
  return src.slice(i,j);
}
const keySrc=extract(candAi,'    function partRegionKey(r) {','\n    function queueEditZones');
const ownerSrc=extract(candAi,'    function partOwnerCurrent(z, key) {','\n    function currentPartZoneOwners(parts, hits)');
const proofSrc=extract(candAi,'    function currentPartZoneOwners(parts, hits) {','\n    function registerAppliedPartZones');
function maskHash(m) { let h=2166136261; for(let i=0;i<m.length;i++) h=Math.imul(h^(Number(m[i])&255),16777619); return m.length+':'+(h>>>0).toString(36); }
const region={layers:['Car Paint'],island:'roof'}, zoneMask=new Uint8Array([1,0,1]), carMask=new Uint8Array([1,1,0]);
const zone={id:'roof-1',name:'Roof repaint',muted:false,regionMask:zoneMask,useRegion:true,_aiPartProv:{r:JSON.stringify(region),z:maskHash(zoneMask),p:maskHash(carMask),l:'layout-1',e:'element-1'}};
const proofCtx={zones:[zone],_editRegSig:'car-sig',_editReg:{},carSig:()=> 'car-sig',CAR:{layoutSig:()=> 'layout-1',maskFor:()=>({mask:carMask})},window:{SpbProElements:{sig:()=> 'element-1'}}};
vm.createContext(proofCtx); vm.runInContext(keySrc+'\n'+ownerSrc+'\n'+proofSrc+'\nthis.editKey=editKey;this.currentPartZoneOwners=currentPartZoneOwners;',proofCtx);
const ownerKey=proofCtx.editKey(region); proofCtx._editReg[ownerKey]='Roof repaint';
const actualProAiCallback=(parts,hits)=>proofCtx.currentPartZoneOwners(parts,hits);
const currentHit=[{zone_id:'roof-1',zone:'Roof repaint',hex:'#1450b4',share:2.9}];
const actualProof=actualProAiCallback(['roof'],currentHit);
assert.strictEqual(actualProof.length,1,'real proAI callback must produce a proof from current region/layout/element/part masks');
assert.strictEqual(actualProof[0].zone_id,'roof-1');

const w = H.load();
vm.runInContext(sources['spb-pro-design.js'], w, {filename:'W31 frozen D'});
vm.runInContext(candEdit, w, {filename:'W31 candidate E'});
const E = w.SpbProEdit;
assert(E && E.plan && E.compile, 'actual candidate E planner/compiler did not load');
const planned = E.plan(cases[0].ask, {palette:[{hex:'#111111',share_pct:42},{hex:'#00b8d4',share_pct:27},{hex:'#eeeeee',share_pct:11}],layers:[],zoneColours:[{hex:'#1450b4',zone_id:'roof-1',zone:'Roof repaint',share_pct:2.9,layers:[]}]});
assert(planned && planned.kind === 'ops' && planned.ops && planned.ops.length === 1 && planned.ops[0].target.kind === 'colour' && planned.ops[0].target.parts && planned.ops[0].target.parts[0] === 'roof', 'actual E.plan did not resolve exact roof colour request: ' + JSON.stringify(planned));
const proof = {zone_id:'roof-1',key:'roof-key',name:'Roof repaint',part:'roof',mask:'mask-current',zoneMask:'zone-mask-current',layout:'layout-1',element:'element-1'};
const zc = [{hex:'#1450b4',zone_id:'roof-1',zone:'Roof repaint',share_pct:2.9,layers:[]}];
const good = E.compile(planned, {palette:[{hex:'#111111',share_pct:42},{hex:'#00b8d4',share_pct:27},{hex:'#eeeeee',share_pct:11}],layers:[],zoneColours:zc,currentPartZoneOwners:actualProAiCallback});
assert(!good.ask && !good.missing.length && good.zones.length===1, 'verified current owner should compile one edit: '+JSON.stringify(good));
assert.strictEqual(String(good.zones[0]._meta.zoneEdit.zone_id), 'roof-1', 'candidate must target the same current UUID');
assert.strictEqual(good.zones[0]._meta.partZoneProof.zone_id, actualProof[0].zone_id, 'compiled edit must carry the real proAI proof token forward');
assert.strictEqual(good.zones[0].color, '#f28bb8', 'expected pale-pink shade operation on current owner');
function compileWith(rows, cb) { return E.compile(planned,{palette:[{hex:'#111111',share_pct:42},{hex:'#00b8d4',share_pct:27},{hex:'#eeeeee',share_pct:11}],layers:[],zoneColours:rows,currentPartZoneOwners:cb}); }
const unsafeCallbacks = [
  {id:'W31-03 changed zone mask', mutate:()=>{zone.regionMask=new Uint8Array([1,1,1]);}},
  {id:'W31-04 CAR mask API missing', mutate:()=>{proofCtx.CAR.maskFor=null;}},
  {id:'W31-04 CAR mask mismatch', mutate:()=>{proofCtx.CAR.maskFor=()=>({mask:new Uint8Array([0,1,1])});}},
  {id:'W31-08 stale layout', mutate:()=>{proofCtx.CAR.layoutSig=()=> 'layout-2';}},
  {id:'W31-08 stale element', mutate:()=>{proofCtx.window.SpbProElements.sig=()=> 'element-2';}},
  {id:'W31-05 duplicate owner', mutate:()=>{proofCtx.zones.push(Object.assign({},zone,{id:'roof-copy'}));}}
];
for(const u of unsafeCallbacks){
  u.mutate(); const cb=actualProAiCallback; assert.strictEqual(cb(['roof'],currentHit).length,0,u.id+' must not issue trusted proof');
  const out=compileWith(zc,cb); assert(out.ask && out.zones.length===0,u.id+' must make the real compiler ask atomically');
  proofCtx.zones.splice(1); zone.regionMask=new Uint8Array([1,0,1]); proofCtx.CAR.maskFor=(part)=>({mask:carMask}); proofCtx.CAR.layoutSig=()=> 'layout-1'; proofCtx.window.SpbProElements.sig=()=> 'element-1';
}
assert.strictEqual(actualProAiCallback(['roof'],[{zone_id:'roof-1',share:0}]).length,0,'W31-06 zero visible footprint must not be trusted');
assert(compileWith([{hex:'#1450b4',zone_id:'roof-1',zone:'Roof repaint',share:0,layers:[]}],actualProAiCallback).ask,'W31-06 hidden current owner must ask');
zone.muted=true; assert.strictEqual(actualProAiCallback(['roof'],currentHit).length,0,'W31-06 muted owner must not be trusted'); zone.muted=false;
assert.strictEqual(actualProAiCallback(['moon panel'],currentHit).length,0,'unknown whole part must not be trusted');
const bodyAndRoof=[{hex:'#1450b4',zone_id:'body-1',zone:'Blue body',share:70,layers:[]},{hex:'#1450b4',zone_id:'roof-1',zone:'Roof repaint',share:2.9,layers:[]}];
const bodyRoofOut=compileWith(bodyAndRoof,actualProAiCallback); assert(bodyRoofOut.ask && bodyRoofOut.zones.length===0,'W31-02 whole-body plus roof ambiguity must fail atomically');
const manual={id:'roof-manual',name:'Roof repaint',muted:false,regionMask:zoneMask,useRegion:true}; proofCtx.zones[0]=manual; proofCtx._editReg[ownerKey]='Roof repaint';
assert.strictEqual(actualProAiCallback(['roof'],currentHit).length,0,'W31-07 matching manual zone must not be adopted');
assert(compileWith(zc,actualProAiCallback).ask,'W31-07 manual owner must ask');
const w27Report = path.join(ROOT, 'docs', 'handoff_reports', 'AI_HELPER_14H_CURRENT_ZONE_COLOUR_SCOPE_RECHECK_2026-10-03.json');
const beforeW27 = crypto.createHash('sha256').update(fs.readFileSync(w27Report)).digest('hex');
const replayReport = path.join(ROOT,'_easy_claude_work','ai14h_w31_candidate','w27_replay.json');
const rerun = execFileSync(process.execPath, [path.join(ROOT,'tests','ai_current_zone_colour_scope_w27_recheck.cjs')], {cwd:ROOT, encoding:'utf8',env:Object.assign({},process.env,{SPB_W27_REPORT_PATH:path.relative(ROOT,replayReport)})});
assert(/14 observations/.test(rerun) && /no fresh credit/.test(rerun), 'W27 same-oracle replay did not complete as no-credit recheck');
const afterW27 = crypto.createHash('sha256').update(fs.readFileSync(w27Report)).digest('hex');
assert.strictEqual(afterW27,beforeW27,'W27 historical report was rewritten during isolated replay');
assert(fs.existsSync(replayReport),'isolated W27 replay report was not written to candidate area');
const results = [
  {id:'W31-01',outcome:'PASS candidate compile: one same-UUID zoneEdit, exact whole-roof callback proof required'},
  ...cases.slice(1).map(c=>({id:c.id,outcome:'PASS fail-closed contract: callback returned no acceptable proof and compiler emitted ask/no zones'}))
];
const report = {id:'W31',status:'isolated-candidate-only',generated_utc:new Date().toISOString(),source_hashes:{task_entry_proAI:'b43d5f6cd4902db8872d862395b4d9ac8be77b22c0b883d01abada507f978dcd',post_parent_undo_fix_frozen_current:Object.fromEntries(Object.keys(hashes).map(n=>[n,hashes[n]])),candidate_proAI:crypto.createHash('sha256').update(candAi).digest('hex'),candidate_E:crypto.createHash('sha256').update(candEdit).digest('hex'),note:'Candidate was rebased from task-entry B43 to current 609 before patching, preserving parent unrelated Undo newline repair.'},fresh_cases:{count:cases.length,sha256:freshSha,results},w23_oracle:{report_sha256:baselineReportSha,preserved:true},w27_oracle:{same_14_case_recheck:'passed; no fresh credit',replay_output:rerun.trim(),isolated_replay_report:path.relative(ROOT,replayReport),existing_report_sha256_before_and_after:beforeW27,original_historical_report_sha256:'946f2021dd8be1fe340c9afab0633e990779a1737e8fd8372414071c07ade365',historical_report_note:'A prior unisolated W27 run refreshed the report timestamp; its original bytes are unavailable, so the original digest is recorded without fabricating restoration. This isolated replay preserved the already-refreshed report.'},candidate_invariants:['currentPartZoneOwners is a proAI callback, not a colour/name heuristic','one exact whole-part scope only; no portion, band, exclude, color selector, whole-body, element, or unknown part selector','requires registered _editReg owner, _aiPartProv, unique current zone with positive visible share, current car signature, unchanged zone mask/layout/element proof, and required CAR.maskFor mask','missing/multiple/stale/muted/manual/hidden proof fails closed','E.compile returns the same owner zone_id and retains partZoneProof on the compiled result'],limits:['This candidate is isolated and not installed in live modules.','Queue/apply must revalidate partZoneProof immediately before edit_zone mutation; this proof harness validates compilation only and does not establish that production integration guard.','Mask behavior is mocked; no live car renderer, native paint, or actual CAR mask implementation was exercised.','It does not establish source-palette overlap resolution when the requested color is also visible in the source paint.','No provider/browser/native tool calls.']};
const reportPath=path.join(ROOT,'docs','handoff_reports','AI_HELPER_14H_OWNED_SCOPED_COLOUR_CANDIDATE_2026-10-03.json');
fs.mkdirSync(path.dirname(reportPath),{recursive:true}); fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');
console.log(`W31 isolated candidate passed ${cases.length} scoped-proof cases; W27 oracle replayed with no new credit.`);
