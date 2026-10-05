// W23 independent safety review of the frozen current zone-colour pathway.
// Cases were frozen before snapshot inspection. Queue and final zone-batch
// callbacks are mocked; no browser, provider, native paint, or live zones run.
const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const H = require('../_easy_claude_work/stack_h.js');
const ROOT = path.resolve(__dirname, '..');
const SNAP = path.join(ROOT, '_easy_claude_work', 'ai14h_w23_sources', 'js');

const cases = [
  { id: 'ZC01', ask: 'Change the blue on the roof to pale pink.', setup: 'unique exact owned roof-blue zone', oracle: 'one edit to same UUID; roof region unchanged' },
  { id: 'ZC02', ask: 'Change only the pink on the roof to pale red.', setup: 'whole-body pink owner plus source pink elsewhere', oracle: 'must not edit whole-body owner for roof-only request' },
  { id: 'ZC03', ask: 'Change the blue on the roof and body to pale red.', setup: 'same color on roof owner and body owner', oracle: 'resolve both only if request explicitly names both complete scopes' },
  { id: 'ZC04', ask: 'Change the blue on the roof and left side to pale red.', setup: 'same color on roof and side helper owners', oracle: 'edit each uniquely owned requested region only' },
  { id: 'ZC05', ask: 'Change the pink on the roof to pale red.', setup: 'overlapping whole-body and roof pink owners', oracle: 'clarify; never guess between overlapping owners' },
  { id: 'ZC06', ask: 'Change the blue on the roof to pale red.', setup: 'only matching owner is muted', oracle: 'do not adopt or edit muted zone; clarify/source-target safely' },
  { id: 'ZC07', ask: 'Change the blue on the roof to pale red.', setup: 'matching owner has zero/currently hidden footprint', oracle: 'do not treat hidden owner color as visible current roof paint' },
  { id: 'ZC08', ask: 'Change the blue on the roof to pale red.', setup: 'duplicate UUID/clone with same color-selector provenance', oracle: 'ambiguous ownership must clarify' },
  { id: 'ZC09', ask: 'Change the blue on the moon panel to pale red.', setup: 'unknown named part', oracle: 'no whole-body fallback or arbitrary matching-zone edit' },
  { id: 'ZC10', ask: 'Change the blue on the car and only the red on the roof to pale pink.', setup: 'whole-body plus named-part constraints', oracle: 'whole-body and roof constraints remain distinct and complete' },
  { id: 'ZC11', ask: 'Change the blue numbers to pale red.', setup: 'whole-body owner linked to a source layer', oracle: 'layer-linked whole region is not adopted as numbers-only owner' },
  { id: 'ZC12', ask: 'Change the blue on the roof to pale red.', setup: 'requested blue exists only in source paint; helper owner is different color', oracle: 'do not confuse source and currently painted colors' },
  { id: 'ZC13', ask: 'Change the blue on the roof to pale red.', setup: 'blue absent from source and no visible owned-blue roof zone', oracle: 'clarify/no queue' },
  { id: 'ZC14', ask: 'Change the blue on the roof to pale pink.', setup: 'unique owner name changed but same selector still exists', oracle: 'renamed/manual/uncertain owner must not be adopted implicitly' }
];
const frozenSha = '9936629743ffa9c6ae0760fd40498215a4c62f3eb1d02dc555386017cfd57270';
assert.strictEqual(crypto.createHash('sha256').update(JSON.stringify(cases)).digest('hex'), frozenSha, 'W23 frozen scenarios changed');

const expectedHashes = {
  'spb-pro-ai.js': '93bf5627e8bad72b8777a6438a7db9ec1ce167af7478afdb15ec643caf0712bb',
  'spb-pro-edit.js': '868e698dd0dc6a3424d5bcb2612bc0f8f21dc7c6ca3ffa6ea2524193cd76078e',
  'spb-pro-design.js': '0533393ff5f2170236f60d4ed489c7ae52f98805e12b0764da67a967f756f2e8'
};
function readPinned(file) {
  const b = fs.readFileSync(path.join(SNAP, file));
  const hash = crypto.createHash('sha256').update(b).digest('hex');
  assert.strictEqual(hash, expectedHashes[file], `pinned W23 snapshot hash mismatch: ${file}`);
  return b.toString('utf8');
}
const proAiSource = readPinned('spb-pro-ai.js');
const editSource = readPinned('spb-pro-edit.js');
const designSource = readPinned('spb-pro-design.js');
function extract(source, startText, endText, label) {
  const start = source.indexOf(startText), end = source.indexOf(endText, start);
  assert(start >= 0 && end > start, `could not extract actual ${label}`);
  return source.slice(start, end);
}
const zoneLayerNamesSrc = extract(proAiSource, '    function zoneLayerNames(z) {', '\n    function zoneColours()', 'zoneLayerNames');
const zoneColoursSrc = extract(proAiSource, '    function zoneColours() {', '\n    // how much of each flattened-paint colour', 'zoneColours');
const queueEditZonesSrc = extract(proAiSource, '    function queueEditZones(cm, addFn, editFn, opts) {', '\n    // ------------------------------------------------------------------ NUMBERS ON A FLAT PAINT', 'queueEditZones');
const applyQueueSrc = extract(proAiSource, '    function applyQueue(queue, label, noUndo, elementIdentity) {', '\n    function partRegHas', 'applyQueue');
const offlineEditAskSrc = extract(proAiSource, '    function offlineEditAsk(text, ed, o) {', '\n    function offlineAsk(text, o)', 'offlineEditAsk');
const offlineAskSrc = extract(proAiSource, '    function offlineAsk(text, o) {', '\n    function offlineAskCore(text, o)', 'offlineAsk');
assert(offlineEditAskSrc.includes('E.compile(ed, env)') && offlineEditAskSrc.includes('queueEditZones(cm, addT.handler, editT.handler)'),
  'the normal offline edit route must compile and queue through the production zone-owner path');
assert(offlineAskSrc.includes('offlineEditAsk('), 'the production offline router must dispatch to offlineEditAsk');

const w = H.load();
vm.runInContext(designSource, w, { filename: 'pinned/spb-pro-design.js' });
vm.runInContext(editSource, w, { filename: 'pinned/spb-pro-edit.js' });
const E = w.SpbProEdit;
assert(E && E.plan && E.compile, 'pinned E planner/compiler did not load');
const sourcePalette = [
  { hex: '#111111', share_pct: 42 }, { hex: '#00b8d4', share_pct: 27 },
  { hex: '#eeeeee', share_pct: 11 }, { hex: '#e7c547', share_pct: 6 },
  { hex: '#42934a', share_pct: 2 }
];
function z(id, name, hex, share, scope, opts) {
  opts = opts || {};
  return {
    id, name, baseColorMode: 'solid', baseColor: hex, muted: !!opts.muted,
    sourceLayerIds: opts.layerIds || [], _regionDesc: { scope }, regionMask: new Uint8Array([1]), useRegion: true,
    share_pct: share, visible_pct: opts.visible_pct != null ? opts.visible_pct : share
  };
}
function productionZoneColours(zoneList) {
  const ctx = { zones: zoneList, Z: { footprint: i => ({ share_pct: zoneList[i].share_pct, visible_pct: zoneList[i].visible_pct }) },
    zoneSourceLayerIds: zz => zz.sourceLayerIds || [], _psdLayers: [{ id: 'numbers-src', name: 'Numbers' }] };
  vm.createContext(ctx);
  vm.runInContext(`${zoneLayerNamesSrc}\n${zoneColoursSrc}\nthis.zoneColours = zoneColours;`, ctx, { filename: 'pinned-zoneColours.js' });
  return ctx.zoneColours();
}
function fixtures(id) {
  const q = {
    ZC01: [z('roof-blue', 'Roof repaint', '#1450b4', 18, 'roof')],
    ZC02: [z('pink-body', 'Pink body', '#ff3fa4', 78, 'whole-body')],
    ZC03: [z('blue-roof', 'Blue roof', '#1450b4', 16, 'roof'), z('blue-body', 'Blue body', '#1450b4', 78, 'whole-body')],
    ZC04: [z('blue-roof', 'Blue roof', '#1450b4', 16, 'roof'), z('blue-side', 'Blue left side', '#1450b4', 24, 'left-side')],
    ZC05: [z('pink-body', 'Pink body', '#ff3fa4', 78, 'whole-body'), z('pink-roof', 'Pink roof', '#ff3fa4', 16, 'roof')],
    ZC06: [z('muted-blue', 'Muted blue roof', '#1450b4', 16, 'roof', { muted: true })],
    ZC07: [z('hidden-blue', 'Hidden blue roof', '#1450b4', 18, 'roof', { visible_pct: 0 })],
    ZC08: [z('clone-blue', 'Cloned blue roof', '#1450b4', 16, 'roof'), z('clone-blue', 'Cloned blue roof copy', '#1450b4', 16, 'roof')],
    ZC09: [z('body-blue', 'Blue body', '#1450b4', 78, 'whole-body')],
    ZC10: [z('blue-body', 'Blue body', '#1450b4', 78, 'whole-body'), z('red-roof', 'Red roof', '#c8102e', 16, 'roof')],
    ZC11: [z('blue-layer', 'Blue layer zone', '#1450b4', 28, 'whole-body', { layerIds: ['numbers-src'] })],
    ZC12: [z('red-roof', 'Red roof', '#c8102e', 16, 'roof')],
    ZC13: [],
    ZC14: [z('manual-blue', 'Renamed blue body', '#1450b4', 78, 'whole-body')]
  }[id];
  return q.map(row => Object.assign({}, row));
}
function sourceFor(id) {
  return id === 'ZC12' ? sourcePalette.concat([{ hex: '#1450b4', share_pct: 3 }]) : sourcePalette;
}
function executeQueueAndApply(cm, zoneList) {
  const qctx = {
    zones: zoneList,
    _editReg: {}, _editRegSig: null, _editRegPendingBefore: {},
    carSig: () => 'fixture-car', editPlural: () => false, friendlyZoneError: x => String(x),
    window: {}, console
  };
  qctx.window = qctx;
  vm.createContext(qctx);
  vm.runInContext(`${queueEditZonesSrc}\nthis.queueEditZones = queueEditZones;`, qctx, { filename: 'pinned-queueEditZones.js' });
  const queued = [];
  const qo = qctx.queueEditZones(cm, spec => ({ spec }), spec => {
    const zi = zoneList.findIndex(row => String(row.id) === String(spec.zone_id));
    if (zi < 0) return { error: 'missing id' };
    queued.push({ kind: 'edit', zone: zi, spec: JSON.parse(JSON.stringify(spec)) });
    return {};
  });
  let committedBatch = [];
  qctx._gen = 0; qctx._layerUndoStack = [];
  qctx.elementRunCurrent = () => true; qctx.rollbackPendingPartRegistry = () => {};
  qctx.applyLayerOps = () => ({ lines: [], failed: [], undoSteps: 0 });
  qctx.partRegistryState = () => ({}); qctx.registerAppliedPartZones = () => {};
  qctx.reconcilePartRegistry = () => {}; qctx.clearPartRegistryPending = () => {};
  qctx.partOwnerCurrent = () => true;
  qctx.Z = { batch: ops => { committedBatch = ops.map(op => JSON.parse(JSON.stringify(op))); return ops.map((op, i) => ({ ok: true, applied: ['set color'], index: op.zone, name: zoneList[op.zone] && zoneList[op.zone].name })); } };
  vm.runInContext(`${applyQueueSrc}\nthis.applyQueue = applyQueue;`, qctx, { filename: 'pinned-applyQueue.js' });
  const applied = qctx.applyQueue(queued, 'W23 synthetic apply', false, null);
  return { queueSummary: qo, queued, committedBatch, applied };
}
function observe(c) {
  const zoneList = fixtures(c.id), zc = productionZoneColours(zoneList), env = {
    palette: sourceFor(c.id), layers: c.id === 'ZC11' ? [{ name: 'Numbers', role: 'numbers', hidden: false }] : [], zoneColours: zc
  };
  const plan = E.plan(c.ask, env), cm = plan && plan.kind === 'ops' ? E.compile(plan, env) : null;
  const result = {
    id: c.id, ask: c.ask, setup: c.setup, oracle: c.oracle,
    ownerRecords: zc,
    planned: plan && { kind: plan.kind, text: plan.text, ops: (plan.ops || []).map(op => ({ target: op.target, colour: op.colour })) },
    compiled: cm && { ask: cm.ask && cm.ask.text, missing: cm.missing || [], zones: cm.zones.map(zz => ({ name: zz.name, color: zz.color, finish: zz.finish, region: zz.region, zoneEdit: zz._meta && zz._meta.zoneEdit, parts: zz._meta && zz._meta.parts })) }
  };
  if (cm && cm.zones.length && cm.zones.every(zz => zz._meta && zz._meta.zoneEdit)) result.queueApply = executeQueueAndApply(cm, zoneList);
  return result;
}
const outcomes = cases.map(observe);
const c1 = outcomes.find(x => x.id === 'ZC01');
assert.strictEqual(c1.compiled.ask, null, 'unique current owner should compile without clarification');
assert.strictEqual(c1.compiled.zones.length, 1);
assert.strictEqual(c1.compiled.zones[0].zoneEdit.zone_id, 'roof-blue');
assert.strictEqual(c1.compiled.zones[0].region, undefined, 'zone-color edit must preserve current mask by omitting region');
assert(c1.queueApply && c1.queueApply.committedBatch.length === 1, 'actual extracted queue/apply path should make one mocked owner edit');
assert.strictEqual(c1.queueApply.committedBatch[0].spec.zone_id, 'roof-blue');
assert.strictEqual(c1.queueApply.committedBatch[0].spec.region, undefined);
const c2 = outcomes.find(x => x.id === 'ZC02');
assert.strictEqual(c2.compiled.zones[0].zoneEdit.zone_id, 'pink-body', 'audit must expose whole-body owner adoption on roof-only request');
assert.strictEqual(c2.compiled.zones[0].region, undefined);
assert(c2.queueApply && c2.queueApply.committedBatch[0].spec.zone_id === 'pink-body', 'queue/apply should demonstrate actual overbroad target');
const c3 = outcomes.find(x => x.id === 'ZC03');
assert(c3.compiled.zones.some(x => x.region && x.region.everything), 'mixed whole-body/part wording must expose its broad additional zone');
const c4 = outcomes.find(x => x.id === 'ZC04');
assert(c4.compiled.zones.some(x => x.region && x.region.part === 'left side'), 'mixed roof/side wording must expose its additional side zone');
const c5 = outcomes.find(x => x.id === 'ZC05');
assert(c5.compiled.zones.length >= 2 && c5.compiled.zones.every(x => x.zoneEdit), 'overlapping matching zone colors must remain observable');
const c6 = outcomes.find(x => x.id === 'ZC06');
const c7 = outcomes.find(x => x.id === 'ZC07');
assert(c6.ownerRecords.length === 0, 'production zoneColours must exclude muted rows');
assert(c7.ownerRecords.length === 1 && c7.ownerRecords[0].share_pct === 0, 'fixture must expose a selected but fully hidden owner');
assert(c7.compiled.zones.some(zz => zz.zoneEdit && zz.zoneEdit.zone_id === 'hidden-blue'), 'hidden owner should be exposed as an unsafe current-color match');
const c11 = outcomes.find(x => x.id === 'ZC11');
assert(c11.compiled.zones.some(zz => zz.region && zz.region.layers && zz.region.layers.indexOf('Numbers') >= 0), 'layer-target request should retain a numbers-layer selector');

const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const report = {
  title: 'W23 current zone-colour scope safety review',
  generated_at: new Date().toISOString(),
  mode: 'read-only pinned-source helper audit with mocked queue/apply callbacks; no provider/browser/native pixels',
  frozen_scenarios_sha256: frozenSha,
  frozen_scenario_count: cases.length,
  pinned_source_hashes: expectedHashes,
  supplied_native_snapshot_scope: {
    gen2_loaded_pro_ai_prefix: '115f', gen2_loaded_edit_prefix: 'd4cd',
    limitation: 'Parent reports the native generation-2 session used these older loaded snapshots, which lack this report’s zoneColours/shownShares and E zoneEdit pathway. The native miss belongs to that old loaded code; this W23 review evaluates only the pinned newer 93bf/868e source snapshots, not what was installed in gen2.'
  },
  actual_functions_exercised: {
    pro_ai_zoneLayerNames: sha(zoneLayerNamesSrc), pro_ai_zoneColours: sha(zoneColoursSrc),
    pro_ai_queueEditZones: sha(queueEditZonesSrc), pro_ai_applyQueue: sha(applyQueueSrc),
    offline_edit_ask: sha(offlineEditAskSrc), offline_ask: sha(offlineAskSrc),
    edit_plan_and_compile: 'executed directly from pinned spb-pro-edit.js; zone-edit queue and applyQueue executed from pinned spb-pro-ai.js with callbacks that capture/mimic successful Zone.batch only. offlineEditAsk/offlineAsk were source-checked for the production compile/dispatch call chain, not invoked as whole UI flows.'
  },
  findings: {
    current_color_owner_scope_gap: 'zoneColours() emits solid-zone id/name/color/coverage/layers but no region, selector, part scope, or helper provenance. E.zoneHits() matches by color family/name (and optional layer names) but ignores requested part; zoneColourOps() emits zoneEdit with zone_id only. queueEditZones() turns that into edit_zone {zone_id,color,...} and applyQueue batches it with no part guard. Thus a whole-body pink owner is edited for “only the pink on the roof.”',
    ambiguity: 'multiple matching owner records are all turned into edits; no uniqueness/overlap guard appears in this pathway. A matching manual/renamed solid zone is eligible because the harvested record has no helper-ownership filter. Rows with selected share > 0 but visible_pct = 0 survive zoneColours() and still match because E.zoneHits() does not filter zero visible share.',
    muted_empty: 'actual zoneColours() excludes muted zones and zones with nonpositive selected footprint. It can retain an entirely hidden selection (visible_pct = 0) when its selected share is positive.',
    preservation: 'For a uniquely matched row, zoneEdit omits region and the queue payload carries only the original zone id and requested color, preserving existing region/mask/material fields at the edit interface.'
  },
  historical_w22_context: 'W22 tested the newer current source and a synthetic fresh owner row. Its conditional E compiler capability is not native generation-2 acceptance and does not show that loaded generation-2 code contained the owner-color pathway.',
  acceptance_limits: [
    'Final Zone.batch/pixel effects are mocked; the test proves actual queue fields and actual applyQueue batch specs, not real masks or rendered pixels.',
    'Zone fixture region scopes are scenario labels only: the actual production zoneColours extractor does not read them, which is part of the observed scope loss.',
    'The live E source changed after the pinned 868e snapshot to 1412ae…; no current-live acceptance is claimed and that writer was not read or tested.',
    'No producer 9/10 tail-positive result is re-credited as fresh evidence by these independent adversarial cases.'
  ],
  outcomes
};
const reportPath = path.join(ROOT, 'docs', 'handoff_reports', 'AI_HELPER_14H_CURRENT_ZONE_COLOUR_SCOPE_REVIEW_2026-10-03.json');
fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
const unsafe = ['ZC02', 'ZC03', 'ZC04', 'ZC05', 'ZC07', 'ZC08', 'ZC14'].filter(id => {
  const row = outcomes.find(x => x.id === id);
  return row && row.compiled && row.compiled.zones.length;
});
console.log(`W23 pinned review recorded ${cases.length} scenarios; demonstrated scope hazards=${unsafe.join(',')}; report=${path.relative(ROOT, reportPath)}`);


