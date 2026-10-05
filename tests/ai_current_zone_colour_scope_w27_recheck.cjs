// W27 same-oracle replay against separately frozen current source bytes.
// This is a recheck, not new coverage credit. Queue and final zone-batch
// callbacks are mocked; no browser, provider, native paint, or live zones run.
const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const H = require('../_easy_claude_work/stack_h.js');
const ROOT = path.resolve(__dirname, '..');
const SNAP = path.join(ROOT, '_easy_claude_work', 'w27_sources', 'js');

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
  'spb-pro-ai.js': '92c247c9ed08617e86d44c48fcbb22dcfb1db61de045bb5e98007899e2c7be51',
  'spb-pro-edit.js': '5e8cc8bb52825b4ebac672a991d6d927b0e5c1906c6d54e80970fb79e18ac456',
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
const shownSharesSrc = extract(proAiSource, '    function shownShares(pal, zc) {', '\n    // numbers / sponsors / stripes on a FLAT paint', 'shownShares');
const queueEditZonesSrc = extract(proAiSource, '    function queueEditZones(cm, addFn, editFn, opts) {', '\n    // ------------------------------------------------------------------ NUMBERS ON A FLAT PAINT', 'queueEditZones');
const applyQueueSrc = extract(proAiSource, '    function applyQueue(queue, label, noUndo, elementIdentity) {', '\n    function partRegHas', 'applyQueue');
const offlineEditAskSrc = extract(proAiSource, '    function offlineEditAsk(text, ed, o) {', '\n    function offlineAsk(text, o)', 'offlineEditAsk');
const offlineAskSrc = extract(proAiSource, '    function offlineAsk(text, o) {', '\n    function offlineAskCore(text, o)', 'offlineAsk');
const offlineScopeGuard = offlineEditAskSrc.indexOf('if (cm.ask || (cm.missing && cm.missing.length))');
const zoneQueueCall = offlineEditAskSrc.indexOf('queueEditZones(cm, addT.handler, editT.handler)');
assert(offlineScopeGuard >= 0 && zoneQueueCall > offlineScopeGuard, 'offlineEditAsk must reject incomplete plans before queueing any component');
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
  const ctx = { zones: zoneList, Z: { footprint: i => ({ share_pct: zoneList[i].share_pct, visible_pct: zoneList[i].visible_pct }),
    probeRegion: r => (r.colors && r.colors[0] === '#1450b4' && zoneList.some(zz => zz.id === 'red-roof'))
      ? { takes_pixels_from: [{ zone: 'Red roof', pct_of_region: 100 }] } : null },
    zoneSourceLayerIds: zz => zz.sourceLayerIds || [], _psdLayers: [{ id: 'numbers-src', name: 'Numbers' }] };
  vm.createContext(ctx);
  vm.runInContext(`${zoneLayerNamesSrc}\n${zoneColoursSrc}\n${shownSharesSrc}\nthis.zoneColours = zoneColours; this.shownShares = shownShares;`, ctx, { filename: 'pinned-zone-colour-pipeline.js' });
  return { rows: ctx.zoneColours(), shownPalette: palette => ctx.shownShares(palette, ctx.zoneColours()) };
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
  const zoneList = fixtures(c.id), zPipe = productionZoneColours(zoneList), zc = zPipe.rows, env = {
    palette: zc.length ? zPipe.shownPalette(sourceFor(c.id)) : sourceFor(c.id),
    layers: c.id === 'ZC11' ? [{ name: 'Numbers', role: 'numbers', hidden: false }] : [], zoneColours: zc
  };
  const plan = E.plan(c.ask, env), cm = plan && plan.kind === 'ops' ? E.compile(plan, env) : null;
  const result = {
    id: c.id, ask: c.ask, setup: c.setup, oracle: c.oracle,
    ownerRecords: zc,
    planned: plan && { kind: plan.kind, text: plan.text, ops: (plan.ops || []).map(op => ({ target: op.target, colour: op.colour })) },
    compiled: cm && { ask: cm.ask && cm.ask.text, missing: cm.missing || [], objects: cm.objects || [], zones: cm.zones.map(zz => ({ name: zz.name, color: zz.color, finish: zz.finish, region: zz.region, zoneEdit: zz._meta && zz._meta.zoneEdit, parts: zz._meta && zz._meta.parts })) }
  };
  if (cm && !cm.ask && !(cm.missing && cm.missing.length) && cm.zones.length && cm.zones.every(zz => zz._meta && zz._meta.zoneEdit)) result.queueApply = executeQueueAndApply(cm, zoneList);
  return result;
}
const outcomes = cases.map(observe);
const baselinePath = path.join(ROOT, 'docs', 'handoff_reports', 'AI_HELPER_14H_CURRENT_ZONE_COLOUR_SCOPE_REVIEW_2026-10-03.json');
const baselineBytes = fs.readFileSync(baselinePath);
const baselineSha = crypto.createHash('sha256').update(baselineBytes).digest('hex');
assert.strictEqual(baselineSha, 'daf2060420db29468bda205d5da12e882bd59f84ea495e208270493b780744d1', 'W23 868e failure evidence changed');
const baseline = JSON.parse(baselineBytes.toString('utf8'));
assert.strictEqual(baseline.frozen_scenarios_sha256, frozenSha, 'W23 baseline used a different frozen oracle');
const noQueueIds = ['ZC01', 'ZC02', 'ZC03', 'ZC04', 'ZC05', 'ZC06', 'ZC07', 'ZC08', 'ZC10', 'ZC13', 'ZC14'];
noQueueIds.forEach(id => {
  const row = outcomes.find(x => x.id === id);
  assert(row && (!row.queueApply || !row.queueApply.committedBatch.length), `${id}: current replay must not send a scoped/mixed request to a mocked mutation batch`);
});
assert(outcomes.find(x => x.id === 'ZC01').compiled.ask, 'current owner without proven part scope should fail closed with clarification');
assert(outcomes.find(x => x.id === 'ZC09').compiled.objects.some(x => x.object === 'moon panel'), 'unknown object target should remain a non-zone object request, not become body paint');
assert(outcomes.find(x => x.id === 'ZC11').compiled.zones.some(x => x.region && x.region.layers && x.region.layers.indexOf('Numbers') >= 0), 'numbers request should retain its layer selector');
assert(outcomes.find(x => x.id === 'ZC12').compiled.ask, 'source-blue masked by a differently-colored roof owner should clarify instead of adding an overlay');
assert(offlineEditAskSrc.includes('E.compile(ed, env)') && zoneQueueCall > offlineScopeGuard,
  'actual offline edit route must reject ask/missing partial plans before queueing');

const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const report = {
  title: 'W27 same-oracle current zone-colour scope recheck',
  generated_at: new Date().toISOString(),
  mode: 'same 14-case W23 replay only; no new fresh coverage credit; frozen source helper audit with mocked queue/apply callbacks; no provider/browser/native pixels',
  frozen_scenarios_sha256: frozenSha,
  frozen_scenario_count: cases.length,
  pinned_source_hashes: expectedHashes,
  baseline_w23_failure_record: { report: 'docs/handoff_reports/AI_HELPER_14H_CURRENT_ZONE_COLOUR_SCOPE_REVIEW_2026-10-03.json', sha256: baselineSha, source_edit_sha256: baseline.pinned_source_hashes['spb-pro-edit.js'], no_rewrite: true, fresh_credit: false },
  runtime_snapshot_scope: {
    parent_reported_hot2_loaded_prefixes: { pro_ai: '65ad', pro_edit: '5e8c' },
    recheck_snapshot_prefixes: { pro_ai: '92c2', pro_edit: '5e8c' },
    limitation: 'The replay evaluates frozen current source bytes only. Parent reports hot2 loaded E 5e8c with older proAI 65ad; this frozen recheck uses proAI 92c2 and does not certify that loaded native route or live rendering.'
  },
  actual_functions_exercised: {
    pro_ai_zoneLayerNames: sha(zoneLayerNamesSrc), pro_ai_zoneColours: sha(zoneColoursSrc),
    pro_ai_shownShares: sha(shownSharesSrc),
    pro_ai_queueEditZones: sha(queueEditZonesSrc), pro_ai_applyQueue: sha(applyQueueSrc),
    offline_edit_ask: sha(offlineEditAskSrc), offline_ask: sha(offlineAskSrc),
    edit_plan_and_compile: 'executed directly from pinned spb-pro-edit.js. queueEditZones/applyQueue and offlineEditAsk/offlineAsk were extracted and source-checked, but none of the current scoped cases passes the clarification guard, so no W27 case entered a zone-edit batch and no whole UI flow was invoked.'
  },
  findings: {
    part_scope_guard: 'Compared with baseline E 868e, current E 5e8c now asks “which also covers other places” when a part-scoped color target has a matching zone color but no matching source-palette color. The 11 frozen same-oracle scoped/mixed cases asserted below have no committed mutation batch. This is fail-closed behavior, but it also asks on ZC01 even though the fixture labels the unique owner as an exact roof zone: proAI.zoneColours() still does not transmit verifiable part/mask provenance to E.',
    baseline_hazards_not_recredited: 'The original W23 report/hash is preserved. Cases that previously edited whole-body, overlapping, hidden, duplicate, or manually named owners now produce clarification/no batch in this source replay; those observations are regression comparison only, not fresh prompt coverage.',
    source_present_and_other_routes: 'With the fixture mask-probe stub, source blue hidden by a red roof owner has shown_pct 0 and ZC12 clarifies rather than adding an overlay. ZC11 compiles a Numbers-layer region. ZC09 is represented as an object target, with no paint zone. ZC10 creates an earlier component before a later scope clarification, but offlineEditAsk checks cm.ask/missing before queueEditZones, so the combined plan is rejected atomically before mutation.',
    remaining_design_need: 'Safe reuse needs a proof-bearing zoneColours record: exact canonical part/portion selector plus current mask/layout identity, active/unmuted state, unique UUID/owner and helper-owned registry provenance. If exact owner proof is missing, overlapping, hidden, duplicate, or manual, clarify. For explicit whole-car color requests, intentional edits to visible matching manual zones may remain allowed with unique active target IDs. Keep source paint colors separate from colors currently painted by zones; never adopt an unrelated source-color zone to satisfy a current-color request.'
  },
  historical_w22_context: 'W22 tested the newer current source and a synthetic fresh owner row. Its conditional E compiler capability is not native generation-2 acceptance and does not show that loaded generation-2 code contained the owner-color pathway.',
  acceptance_limits: [
    'The no-queue scoped cases assert that no committed mutation batch is produced. Queue/apply callbacks were not reached by the current W27 cases because they fail closed earlier.',
    'Zone fixture region scopes are scenario labels only: production zoneColours still omits region/part proof. Thus ZC01 is expected to fail closed pending a proof hook.',
    'No native app, live paint, or post-freeze source was read or tested; current-live acceptance is not claimed.',
    'The identical W23 oracle is replayed for regression comparison only; no producer 9/10 tail-positive result or prompt gets fresh credit.'
  ],
  outcomes
};
const reportPath = process.env.SPB_W27_REPORT_PATH ? path.resolve(ROOT, process.env.SPB_W27_REPORT_PATH) : path.join(ROOT, 'docs', 'handoff_reports', 'AI_HELPER_14H_CURRENT_ZONE_COLOUR_SCOPE_RECHECK_2026-10-03.json');
fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
const unsafe = ['ZC02', 'ZC03', 'ZC04', 'ZC05', 'ZC07', 'ZC08', 'ZC14'].filter(id => {
  const row = outcomes.find(x => x.id === id);
  return row && row.compiled && row.compiled.zones.length;
});
console.log(`W27 same-oracle replay recorded ${cases.length} observations; scoped/mixed batch rejections=${noQueueIds.length}; no fresh credit; report=${path.relative(ROOT, reportPath)}`);





