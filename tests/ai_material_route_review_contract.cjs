// W8 route oracle, frozen before inspecting offlineMaterialPlan/offlineMaterialAsk.
// The harness below will bind these scenarios to the existing offline routing seams.
const FRESH_ORACLE = Object.freeze([
  { id: 'c07-default-shift', input: 'Everything is too shiny; lower clearcoat on roof only.', expected: 'queue-clearcoat-minus-20' },
  { id: 'c07-preserve-other-shifts', setup: 'current R/G offsets are nonzero', expected: 'only-clearcoat-offset-changes' },
  { id: 'preserve-finish-and-colors', setup: 'zone has base finish and color fields', expected: 'spec-only-edit' },
  { id: 'preserve-pattern-and-mask', setup: 'zone has pattern and mask fields', expected: 'spec-only-edit' },
  { id: 'missing-part', setup: 'no current target part', expected: 'ask-no-queue' },
  { id: 'muted-part', setup: 'target part is muted', expected: 'ask-no-queue' },
  { id: 'renamed-part', setup: 'part changed name after request', expected: 'ask-no-queue' },
  { id: 'stale-part', setup: 'part identity is stale', expected: 'ask-no-queue' },
  { id: 'ambiguous-owner', setup: 'two live zones claim the requested part', expected: 'ask-no-queue' },
  { id: 'unknown-subpart', input: 'lower clearcoat on the roof spoiler lip', expected: 'ask-no-queue' },
  { id: 'stale-offset-plan', setup: 'zone offsets change after queue plan is built', expected: 'refuse-stale-plan' },
  { id: 'successful-edit-undo', setup: 'valid unique current part and current offsets', expected: 'normal-edit-queue-and-undo' },
  { id: 'failed-queue-no-spec-mutation', setup: 'normal edit queue rejects request', expected: 'no-spec-mutation-and-error-undo' },
  { id: 'protected-part-first', input: 'lower clearcoat on a protected decal', expected: 'protected-part-ask-before-material-plan' },
  { id: 'ineligible-material-routing', setup: 'configured material-edit eligibility is false', expected: 'delegate-no-queue' },
  { id: 'mixed-decorative-action', input: 'lower clearcoat on roof and make it Flame Lapped', expected: 'delegate-no-material-queue' },
  { id: 'question-howto', input: 'How do I lower clearcoat on the roof?', expected: 'delegate-no-queue' },
  { id: 'decorative-pattern-request', input: 'make roof look like Flame Lapped Clearcoat', expected: 'decorative-path-no-material-edit' },
  { id: 'nonmaterial-request', input: 'change roof color to blue', expected: 'delegate-no-queue' },
  { id: 'registry-owner-stale', setup: 'current owner registry no longer proves part ownership', expected: 'ask-no-queue' },
]);
// Post-oracle mixed-prefix regressions requested after a separate source finding.
const POST_ORACLE_MIXED_PREFIX = Object.freeze([
  { id: 'hood-paint-action-in-observational-preface', text: 'Paint the hood red and the roof looks too shiny; lower clearcoat on the roof only.' },
  { id: 'diagnostic-label-with-paint-action', text: 'Diagnostic: paint the hood red; lower clearcoat on the roof only.' },
]);
// Post-oracle intent-ownership cases: explicit material verbs declined by the
// channel parser must receive a safe clarification before decorative routing.
const POST_ORACLE_DECLINED_INTENTS = Object.freeze([
  { id: 'negative-material-command', text: 'Do not lower clearcoat on the roof.' },
  { id: 'question-material-command', text: 'Lower clearcoat on the roof?' },
]);

if (FRESH_ORACLE.length < 16 || new Set(FRESH_ORACLE.map(c => c.id)).size !== FRESH_ORACLE.length) {
  throw new Error('Fresh route oracle must have at least 16 unique cases');
}

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const aiSource = fs.readFileSync(path.join(root, 'js/spb-pro-ai.js'), 'utf8');
const zoneSource = fs.readFileSync(path.join(root, 'js/spb-pro-zone-kit.js'), 'utf8');
const controls = require('../js/spb-ai-material-controls.js');

function extract(src, name) {
  const start = src.indexOf(`function ${name}(`); assert(start >= 0, name);
  const open = src.indexOf('{', start); let depth = 0, quote = null, escape = false, line = false, block = false;
  for (let i = open; i < src.length; i++) {
    const c = src[i], n = src[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (quote) { if (escape) escape = false; else if (c === '\\') escape = true; else if (c === quote) quote = null; continue; }
    if (c === '/' && n === '/') { line = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    else if (c === '}' && --depth === 0) return src.slice(start, i + 1);
  }
  throw Error(`unterminated ${name}`);
}
function cloneZone(z) {
  const c = Object.assign({}, z);
  for (const k of ['regionMask', 'spatialMask', 'patternStrengthMap']) if (z[k] && z[k].length != null) c[k] = new Uint8Array(z[k]);
  return c;
}

function materialHarness() {
  const zones = [], undo = [], model = { car: 'route-car', layout: 'route-layout', elements: 'route-elements' };
  const ctx = { console, Uint8Array, Float32Array, Date, Math, JSON, isFinite, parseInt, zones, selectedZoneIndex: 0,
    BASES: [{ id: 'gloss' }, { id: 'matte' }], MONOLITHICS: [], PATTERNS: [], SPEC_PATTERNS: [],
    _psdLayers: [{ id: 'body', name: 'Body Paint', img: {} }], document: { getElementById: () => ({ width: 32, height: 32 }) },
    addZone() { zones.push({ id: `route-zone-${zones.length + 1}`, name: 'New zone', colorMode: 'none', color: 'source', colors: [] }); },
    duplicateZone(i) { zones.splice(i + 1, 0, cloneZone(zones[i])); },
    assignFinishToSelected(id) { if (zones[ctx.selectedZoneIndex]) zones[ctx.selectedZoneIndex].base = id; },
    setZoneSourceLayer(i, id) { zones[i].sourceLayerIds = id ? [id] : []; }, toggleZoneSourceLayer() {},
    pushZoneUndo() { undo.push(zones.map(cloneZone)); },
    undoZoneChange() { const prior = undo.pop(); if (prior) zones.splice(0, zones.length, ...prior.map(cloneZone)); },
    renderZones() {}, triggerPreviewRender() {}, render() {}, _busy: false, _progress: '', _gen: 0, _snapGen: 0, _activeId: null,
    _log: [], RECENT: [], _advUsed: null, _advRejected: [], applyLayerOps: () => ({ lines: [], failed: [], undoSteps: 0 }),
    carSig: () => model.car, editPlural: () => false, friendlyZoneError: String, warm: () => Promise.resolve(),
    SpbProCar: { findIsland: n => ({ id: String(n), name: String(n), front: true, up: true }), parts: () => ['roof', 'hood'], canon: String,
      signature: () => model.car, layoutSig: () => model.layout, roles: () => [{ role: 'body paint', visible: true, name: 'Body Paint' }],
      maskFor(n) { const mask = new Uint8Array(1024), start = n === 'hood' ? 512 : 0; for (let i = start; i < start + 512; i++) mask[i] = 255; return { mask, island: { name: String(n) }, islands: [{ name: String(n) }] }; } },
    SpbProElements: { sig: () => model.elements }
  };
  ctx.CAR = ctx.SpbProCar; ctx.window = ctx; ctx.SpbMaterialControls = controls; ctx.SpbProElements = ctx.SpbProElements;
  vm.createContext(ctx); vm.runInContext(zoneSource, ctx, { filename: 'production-zone-kit' }); ctx.Z = ctx.SpbProZone;
  const declarations = ['normaliseSpec', 'strip', 'hasSelector', 'bodyLayerNames', 'wantsDecalsToo', 'protectDecals', 'keepOwnColour', 'specOnlyGuard', 'partScopeGuard',
    'partRegionKey', 'editKey', 'setPartEditReg', 'deletePartEditReg', 'partOwnerCurrent', 'partRegHas', 'partRegistryState', 'rollbackPendingPartRegistry',
    'clearPartRegistryPending', 'reconcilePartRegistry', 'registerAppliedPartZones', 'markPartFollowupQueue', 'mergePartRegistryUndo',
    'restorePartRegistryUndo', 'applyQueue', 'doUndo', 'offlineMaterialPlan',
    'offlineMaterialAsk', 'editReply'].map(n => extract(aiSource, n)).join('\n');
  const route = [extract(aiSource, 'offlineMaterialAsk')].join('\n');
  vm.runInContext(`${declarations}\n${route}\nvar _editReg={},_editRegSig=null,_editRegPendingBefore={},_reqText='',_specOnlyReq=false;`, ctx, { filename: 'production-material-route' });
  ctx.editEnv = () => ({}); ctx.captureOriginal = () => {}; ctx.elementRunCurrent = () => true; ctx.panelsNeeded = () => []; ctx.isSchemeRequest = () => false;
  ctx.E = { plan: () => ctx.probe || { kind: 'ops', exactPart: true, ops: [{ target: { kind: 'part', part: 'roof' } }] } };
  const resolver = extract(aiSource, 'resolveZone'), doEdit = extract(aiSource, 'doEdit');
  ctx.makeTools = queue => vm.runInContext(`(function(queue){${resolver}\n${doEdit}\nreturn [{name:'edit_zone',handler:function(a){return doEdit(a,queue);}}];})`, ctx)(queue);
  const added = ctx.Z.add({ name: 'Roof helper', region: { part: 'roof', layers: ['Body Paint'] }, color: '#c8102e', finish: 'base::gloss' });
  assert.equal(added.ok, true, JSON.stringify(added.warnings));
  const z = zones[0]; z.specShiftR = 17; z.specShiftG = -8; z.specShiftB = 46;
  z.base = 'base::gloss'; z.baseColor = '#c8102e'; z.pattern = { id: 'p_keep' }; z.patternOpacity = 42;
  const key = ctx.editKey({ part: 'roof', layers: ['Body Paint'] }); ctx._editReg[key] = z.name; ctx._editRegSig = model.car;
  return { ctx, zones, undo, model, z, key };
}

function priorityHarness() {
  const parses = { count: 0, parse: text => { parses.count++; return controls.parse(text); } };
  const ctx = { console, window: { SpbMaterialControls: parses }, SpbMaterialControls: parses, E: {}, D: null, START_OVER_RE: /^$/, _advLast: null,
    _offlineLast: null, _forcedIdeaCols: null, _busy: false, _progress: '', zones: [], _log: [], _reqText: '', _specOnlyReq: false, _skipParts: true,
    editPlan: () => ctx.editPlanResult, offlineEditAsk: () => { ctx.calls.push('protected'); return 'protected'; },
    offlineMaterialAsk: (text, parsed) => { ctx.calls.push(parsed && parsed.kind === 'clarify' ? 'material-clarify' : 'material'); return parsed && parsed.kind === 'clarify' ? 'clarify' : 'material'; }, captureOriginal() {}, render() {},
    intentSpecOnly: () => true, calls: [], selfHelpClaim: () => null, advisorIntent: () => null, AI: { cached: () => ({ configured: false }) },
    offlineFirst: () => false, askCore: () => { ctx.calls.push('external'); return 'external'; },
    panelsNeeded: () => [], CAR: null, offlineCannot: () => null };
  vm.createContext(ctx);
  vm.runInContext([extract(aiSource, 'offlineMaterialPlan'), extract(aiSource, 'offlineCanHandle'), extract(aiSource, 'offlineAsk'),
    extract(aiSource, 'offlineAskCore'), extract(aiSource, 'ask')].join('\n'), ctx, { filename: 'production-material-routing' });
  return ctx;
}

async function main() {
  let passed = 0;
  const h = materialHarness(), { ctx, zones, undo, z, key } = h;
  const parsed = ctx.offlineMaterialPlan('Everything is too shiny; lower clearcoat on roof only.');
  assert.equal(parsed.kind, 'edit'); assert.equal(parsed.delta, -20); passed++;
  const snapshot = { r: z.specShiftR, g: z.specShiftG, b: z.specShiftB, base: z.base, color: z.baseColor, pattern: JSON.stringify(z.pattern), opacity: z.patternOpacity, mask: Array.from(z.regionMask) };
  const reply = await ctx.offlineMaterialAsk('Everything is too shiny; lower clearcoat on roof only.', parsed);
  assert.equal(reply.queue.length, 1, JSON.stringify({ reply, prov: z._aiPartProv, key, registry: ctx._editReg, current: ctx.partOwnerCurrent(z, key), region: z.region, useRegion: z.useRegion })); assert.deepEqual(Array.from(reply.tools), ['edit_zone']);
  assert.deepEqual(JSON.parse(JSON.stringify(reply.queue[0].spec)), { spec_shift: { metal: 17, rough: -8, clearcoat: 26 } });
  assert.equal(reply.queue[0]._spbPartRegKey, key); assert.equal(reply.queue[0]._spbPartOwnerName, 'Roof helper');
  assert.deepEqual({ r: z.specShiftR, g: z.specShiftG, b: z.specShiftB, base: z.base, color: z.baseColor, pattern: JSON.stringify(z.pattern), opacity: z.patternOpacity, mask: Array.from(z.regionMask) }, snapshot, 'building the queue does not mutate current paint'); passed++;

  const beforeMeta = reply.queue[0]._spbMaterialBefore;
  assert.deepEqual(JSON.parse(JSON.stringify(beforeMeta)), { id: String(z.id), metal: 17, rough: -8, clearcoat: 46 });
  const applied = ctx.applyQueue(reply.queue, 'W8 material route');
  assert.equal(applied.results[0].ok, true, JSON.stringify(applied.results));
  assert.deepEqual([z.specShiftR, z.specShiftG, z.specShiftB], [17, -8, 26]);
  assert.equal(z.base, snapshot.base); assert.equal(z.baseColor, snapshot.color); assert.deepEqual(z.pattern, JSON.parse(snapshot.pattern)); assert.equal(z.patternOpacity, snapshot.opacity); assert.deepEqual(Array.from(z.regionMask), snapshot.mask); passed++;
  const entry = { undoable: true, _partRegUndo: applied.partRegUndo, maskUndo: applied.maskUndo, layerUndo: applied.layerUndo };
  ctx.doUndo(entry); assert.deepEqual([zones[0].specShiftR, zones[0].specShiftG, zones[0].specShiftB], [17, -8, 46]); assert.equal(entry.undone, true); passed++;

  // An older queued operation must fail before ZoneKit and must not create an Undo snapshot.
  const stalePlan = await ctx.offlineMaterialAsk('lower clearcoat on roof only', ctx.offlineMaterialPlan('lower clearcoat on roof only'));
  const undoDepth = undo.length, batch = ctx.Z.batch; let batchCalls = 0;
  ctx.Z.batch = function () { batchCalls++; return batch.apply(ctx.Z, arguments); };
  zones[0].specShiftB = 12;
  const stale = ctx.applyQueue(stalePlan.queue, 'stale material plan');
  assert.equal(stale.results[0].ok, false); assert.match(stale.failed.join(' '), /material settings changed/i);
  assert.equal(batchCalls, 0); assert.equal(undo.length, undoDepth); assert.equal(zones[0].specShiftB, 12); passed++;

  // The same private guard also binds the queued edit to the original zone UUID.
  const uuidHarness = materialHarness();
  const uuidPlan = await uuidHarness.ctx.offlineMaterialAsk('lower clearcoat on roof only', uuidHarness.ctx.offlineMaterialPlan('lower clearcoat on roof only'));
  const uuidUndoDepth = uuidHarness.undo.length, uuidBatch = uuidHarness.ctx.Z.batch; let uuidBatchCalls = 0;
  uuidHarness.ctx.Z.batch = function () { uuidBatchCalls++; return uuidBatch.apply(uuidHarness.ctx.Z, arguments); };
  uuidHarness.zones[0].id = 'replaced-zone-id';
  const uuidRejected = uuidHarness.ctx.applyQueue(uuidPlan.queue, 'stale material zone id');
  assert.equal(uuidRejected.results[0].ok, false); assert.match(uuidRejected.failed.join(' '), /material settings changed/i);
  assert.equal(uuidBatchCalls, 0); assert.equal(uuidHarness.undo.length, uuidUndoDepth); passed++;

  // Target ownership failure modes use the production partOwnerCurrent function.
  async function noQueue(label, mutate) {
    const qh = materialHarness(); if (mutate) mutate(qh);
    const p = qh.ctx.offlineMaterialPlan('lower clearcoat on roof only');
    const r = await qh.ctx.offlineMaterialAsk('lower clearcoat on roof only', p);
    assert.deepEqual(Array.from(r.queue || []), [], `${label}: no queue`); assert.equal(r.tools && Array.from(r.tools).includes('edit_zone'), false, `${label}: no edit tool`); passed++;
  }
  await noQueue('missing target', qh => { qh.ctx.probe = { kind: 'ask' }; });
  await noQueue('muted owner', qh => { qh.zones[0].muted = true; });
  await noQueue('renamed owner', qh => { qh.zones[0].name = 'Roof renamed by user'; });
  await noQueue('stale owner mask', qh => { qh.zones[0].regionMask[0] ^= 255; });
  await noQueue('ambiguous owner', qh => {
    const duplicate = cloneZone(qh.zones[0]); duplicate.id = 'ambiguous-copy'; duplicate.name = 'Second roof helper'; qh.zones.push(duplicate);
  });
  await noQueue('unknown or subpart', qh => { qh.ctx.probe = { kind: 'ops', exactPart: false, ops: [{ target: { kind: 'part', part: 'roof spoiler lip' } }] }; });

  // Priority and configured-provider checks execute the actual production routing functions.
  const ph = priorityHarness();
  ph.D = { compoundPlan: () => { ph.calls.push('compound'); return null; }, offlineIdeas: () => null, lookRequest: () => { ph.calls.push('look'); return null; }, offlineSpec: () => null };
  ph.advisorIntent = () => { ph.calls.push('advisor'); return null; };
  for (const fn of ['offlineAsk', 'offlineAskCore']) {
    ph.calls.length = 0; ph.editPlanResult = { kind: 'ask', protected_parts: ['decal'] };
    assert.equal(await ph[fn]('lower clearcoat on roof only'), 'protected'); assert.deepEqual(ph.calls, ['protected']); passed++;
    ph.calls.length = 0; ph.editPlanResult = { kind: 'ops', exactPart: true };
    assert.equal(await ph[fn]('lower clearcoat on roof only'), 'material'); assert.deepEqual(ph.calls, ['material'], `${fn}: material precedes exact-part, compound and advisor routes`); passed++;
  }
  ph.calls.length = 0; assert.equal(await ph.offlineCanHandle('lower clearcoat on roof only'), true); passed++;
  const routedOfflineAsk = ph.offlineAsk;
  ph.offlineAsk = () => { ph.calls.push('material'); return 'material'; };
  ph.AI.cached = () => ({ configured: false }); assert.equal(await ph.ask('lower clearcoat on roof only'), 'material'); passed++;
  ph.AI.cached = () => ({ configured: true }); ph.offlineFirst = () => true; assert.equal(await ph.ask('lower clearcoat on roof only'), 'material'); passed++;
  ph.AI.cached = () => ({ configured: true }); ph.offlineFirst = () => false; assert.equal(await ph.ask('lower clearcoat on roof only'), 'external'); passed++;
  const sendStart = aiSource.indexOf('function send(text, o)');
  const sendEnd = aiSource.indexOf('function mergeMaskUndo(', sendStart);
  const sendSource = aiSource.slice(sendStart, sendEnd);
  assert.match(sendSource, /_mat0\s*=\s*offlineMaterialPlan\(text\)/); assert.match(sendSource, /\|\|\s*_mat0\s*\|\|/); passed++;

  // Actual planner should not claim a decorative pattern or a question as a material edit.
  const questionPlan = ctx.offlineMaterialPlan('How do I lower clearcoat on roof?');
  assert.notEqual(questionPlan && questionPlan.kind, 'edit');
  const questionReply = await ctx.offlineMaterialAsk('How do I lower clearcoat on roof?', questionPlan);
  assert.deepEqual(Array.from(questionReply.queue || []), []); passed++;
  assert.notEqual(ctx.offlineMaterialPlan('lower clearcoat on roof and make it Flame Lapped').kind, 'edit'); passed++;
  assert.equal(ctx.offlineMaterialPlan('make roof look like Flame Lapped Clearcoat'), null); passed++;
  assert.equal(ctx.offlineMaterialPlan('change roof color to blue'), null); passed++;

  // Structural branch order protects asks first, then material edits, before exact-part/compound/advisor.
  for (const fnName of ['offlineAsk', 'offlineAskCore']) {
    const body = extract(aiSource, fnName);
    const protectedPos = body.indexOf("protectedEdit.kind === 'ask'");
    const materialPos = body.indexOf('var materialEdit = offlineMaterialPlan(text)');
    const exactPos = body.indexOf("protectedEdit.kind === 'ops' && protectedEdit.exactPart");
    assert.ok(protectedPos >= 0 && materialPos > protectedPos && exactPos > materialPos, `${fnName} priority order`); passed++;
  }

  // Post-oracle module and actual material-route checks: a decorative action in
  // a supposed diagnostic prefix cannot be silently dropped into a material edit.
  for (const c of POST_ORACLE_MIXED_PREFIX) {
    const mp = controls.parse(c.text);
    assert.notEqual(mp.kind, 'edit', `${c.id}: parser must reject mixed diagnostic prefix`);
    const rp = ctx.offlineMaterialPlan(c.text);
    assert.notEqual(rp && rp.kind, 'edit', `${c.id}: offline plan must not produce a material edit`);
    const r = await ctx.offlineMaterialAsk(c.text, rp || { kind: 'delegate' });
    assert.deepEqual(Array.from(r.queue || []), [], `${c.id}: no material queue`); passed++;
  }
  for (const c of POST_ORACLE_DECLINED_INTENTS) {
    const raw = controls.parse(c.text); assert.equal(raw.kind, 'delegate', `${c.id}: module declines explicit intent`);
    const plan = ctx.offlineMaterialPlan(c.text); assert.equal(plan.kind, 'clarify', `${c.id}: parent material gate converts decline safely`);
    const safe = await ctx.offlineMaterialAsk(c.text, plan); assert.deepEqual(Array.from(safe.queue || []), [], `${c.id}: no edit queue`);
    ph.D = { compoundPlan: () => null, lookRequest: () => { ph.calls.push('decorative-look'); return { kind: 'pattern' }; }, offlineSpec: () => null };
    ph.offlineLookAsk = () => { ph.calls.push('decorative-apply'); return 'decorative'; };
    ph.editPlanResult = null;
    for (const fn of ['offlineAsk', 'offlineAskCore']) {
      ph.calls.length = 0; const routed = fn === 'offlineAsk' ? routedOfflineAsk : ph[fn]; assert.equal(await routed(c.text), 'clarify');
      assert.deepEqual(ph.calls, ['material-clarify'], `${c.id}/${fn}: decorative pattern/advisor never claims intent`);
    }
    passed++;
  }

  // Parent route channel-key mapping: R=metalness, G=roughness, B=clearcoat.
  for (const c of [
    { text: 'Raise metalness on roof by 7 points.', expected: { metal: 24, rough: -8, clearcoat: 46 } },
    { text: 'Lower roughness on roof by 4 points.', expected: { metal: 17, rough: -12, clearcoat: 46 } },
  ]) {
    const ch = materialHarness(), pp = ch.ctx.offlineMaterialPlan(c.text), rr = await ch.ctx.offlineMaterialAsk(c.text, pp);
    assert.equal(rr.queue.length, 1, JSON.stringify(rr));
    assert.deepEqual(JSON.parse(JSON.stringify(rr.queue[0].spec)), { spec_shift: c.expected }); passed++;
  }

console.log(`PASS ${passed} actual-route checks across ${FRESH_ORACLE.length} frozen scenarios plus mixed-prefix, declined-intent, channel-map and UUID post-oracle cases (native UI/MCP effects mocked)`);
}

main().catch(e => { console.error(e && e.stack || e); process.exitCode = 1; });
module.exports = { FRESH_ORACLE, POST_ORACLE_MIXED_PREFIX, POST_ORACLE_DECLINED_INTENTS };
