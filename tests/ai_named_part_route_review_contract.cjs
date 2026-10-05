'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');

const root = path.resolve(__dirname, '..');
const oraclePath = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_W7_ROUTE_ORACLE_2026-10-03.json');
const oracleHash = 'D66185D7C132EFF94831617862C568ED89A5270022A8D599C20F28577FD9C7E6';
assert.equal(crypto.createHash('sha256').update(fs.readFileSync(oraclePath)).digest('hex').toUpperCase(), oracleHash, 'frozen independent route oracle changed');
const oracle = JSON.parse(fs.readFileSync(oraclePath, 'utf8'));
assert.equal(oracle.cases.length, 16);

function extractFunction(source, name) {
  const start = source.indexOf(`function ${name}(`);
  assert(start >= 0, `actual source function ${name} exists`);
  const brace = source.indexOf('{', start);
  let depth = 0, quote = null, lineComment = false, blockComment = false, escaped = false;
  for (let i = brace; i < source.length; i++) {
    const c = source[i], n = source[i + 1];
    if (lineComment) { if (c === '\n') lineComment = false; continue; }
    if (blockComment) { if (c === '*' && n === '/') { blockComment = false; i++; } continue; }
    if (quote) { if (escaped) { escaped = false; continue; } if (c === '\\') { escaped = true; continue; } if (c === quote) quote = null; continue; }
    if (c === '/' && n === '/') { lineComment = true; i++; continue; }
    if (c === '/' && n === '*') { blockComment = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    if (c === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`unterminated actual source function ${name}`);
}

const w = { console, Promise, document: {} };
w.window = w; vm.createContext(w);
for (const file of ['js/spb-pro-design.js', 'js/spb-pro-edit.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), w, { filename: file });
}
const E = w.SpbProEdit, D = w.SpbProDesign;
const env = {
  palette: [
    { hex: '#141416', share_pct: 52 }, { hex: '#f2c500', share_pct: 22 },
    { hex: '#f1f1ee', share_pct: 14 }, { hex: '#1347a8', share_pct: 5 }
  ], layers: []
};
const aiSource = fs.readFileSync(path.join(root, 'js/spb-pro-ai.js'), 'utf8');
const route = {
  window: Object.assign(w, { SpbMaterialControls: undefined }), console, Promise,
  D, E, START_OVER_RE: /^\s*(?:start over|new design)\b/i,
  SMALL_HELLO_RE: /^\s*(hi|hello)\b/i, SMALL_THANKS_RE: /^\s*(thanks|thank you)\b/i,
  CANT_RE: /$a/, NUM_FIX_RE: /$a/,
  _offlineLast: null, _advLast: null, _advRejected: [], _advDislikes: [], _forcedIdeaCols: null,
  _reqText: '', _specOnlyReq: false, _beforeImg: null, _busy: false, _progress: '',
  _editReg: {}, _editRegPendingBefore: {}, _editRegSig: 'test-car', zones: [], CAR: null,
  captures: 0, advisorCalls: 0, coreCalls: 0, editCalls: 0, providerCalls: 0,
  editPlan: text => E.plan(text, env),
  selfHelpClaim: () => null, advisorIntent: () => { route.advisorCalls++; return null; },
  editYieldsToStack: () => false, captureOriginal() { route.captures++; }, intentSpecOnly: () => false,
  elementRunCurrent: () => true, elementPaintChangedResult: () => ({ cancelled: true }),
  layerVisRequest: () => null, lookEntry: () => null,
  offlineMaterialAsk() { throw new Error('material controls absent in named-part review'); },
  offlineAskCore(text) { route.coreCalls++; return { route: 'core', queue: [], compound: D.compoundPlan(text) || null }; },
  render() {}, warm() { return Promise.resolve(); }, advisorEnv: () => ({}),
  advisorReply() { throw new Error('advisor answer unexpectedly reached route review'); },
  _skipParts: true, _absent: {},
  prepEnv: () => Promise.resolve(env), resolveLook: () => Promise.resolve(null), elementKinds: () => [],
  exclTargets: () => [], markPartFollowupQueue() {}, editOverlapNote: () => '', editOverlapKinds: () => [], exclNotes: () => [],
  makeTools(queue) { return [
    { name: 'add_zone', handler(spec) { const call = { kind: 'add', spec }; queue.push(spec); route.addCalls.push(call); return {}; } },
    { name: 'edit_zone', handler(args) { const call = { kind: 'edit', args }; queue.push(args); route.editCallsList.push(call); return {}; } }
  ]; },
  editReply(text, chips, options) { return { route: options && options.queue ? 'edit' : 'edit-ask', text, queue: options && options.queue ? options.queue : [], options: options || {} }; },
  carSig: () => 'test-car', partRegHas: (obj, key) => Object.prototype.hasOwnProperty.call(obj || {}, key),
  normaliseSpec: spec => spec, protectDecals() {}, friendlyZoneError: String,
  editPlural: label => /(numbers|sponsors|stripes|logos|decals|lines|bands|accents|panels|parts|bumpers)$/.test(String(label)),
  addCalls: [], editCallsList: []
};
route.window = route.window || route;
route.window.SpbProElements = undefined;
route.window.SpbMaterialControls = undefined;
vm.createContext(route);
for (const helper of ['partRegionKey', 'editKey', 'editPlural', 'offlineMaterialPlan', 'queueEditZones', 'offlineCanHandle', 'offlineEditAsk', 'offlineAsk']) {
  vm.runInContext(extractFunction(aiSource, helper), route, { filename: `js/spb-pro-ai.js#${helper}` });
}

function hashMask(mask) {
  let h = 2166136261;
  for (const b of mask) h = Math.imul(h ^ (Number(b) & 255), 16777619);
  return mask.length + ':' + (h >>> 0).toString(36);
}
function seedOwnedPart(part, finish, colour, targetOverride, regionOverride) {
  const target = targetOverride || { kind: 'part', part };
  const regionResult = regionOverride ? { region: regionOverride } : E.regionFor(target, env);
  assert(regionResult && regionResult.region && regionResult.region.part === part, `fixture region exists for ${part}`);
  const region = regionResult.region, key = route.editKey(region), name = `AI-owned ${part}`;
  const mask = new Uint8Array([1, 2, 3, 4]);
  route.zones = [{ id: `existing-${part}`, name, muted: false, regionMask: mask, useRegion: true,
    finishKey: finish, colour, _aiPartProv: { r: JSON.stringify(region), z: hashMask(mask), l: '', e: '' } }];
  route._editReg = { [key]: name };
  route._editRegPendingBefore = {};
  route._editRegSig = 'test-car';
}
function resetCalls() { route.addCalls = []; route.editCallsList = []; route.editCalls = 0; route.coreCalls = 0; route.advisorCalls = 0; }
route.offlineEditAsk = route.offlineEditAsk;
route.offlineCanHandle = route.offlineCanHandle;
route.editPlan = text => E.plan(text, env);
route.advisorIntent = () => { route.advisorCalls++; return null; };
route.offlineAskCore = text => { route.coreCalls++; return { route: 'core', queue: [], compound: D.compoundPlan(text) || null }; };

function partFromQueue(call) {
  if (call.region) return call.region.part;
  const parsed = JSON.parse(call._spbPartRegKey || '{}');
  return parsed.p || null;
}
function scopeFromQueue(call) {
  if (call.region) return call.region.everything || call.region.paintable ? 'body' : call.region.part;
  const parsed = JSON.parse(call._spbPartRegKey || '{}');
  return parsed.e ? 'body' : (parsed.p || null);
}
function isQueuedEdit(call) { return !!(call && call.zone_id); }

(async () => {
  // Route calls use actual offlineAsk; edits compile through E and go through the actual queueEditZones.
  const actualRoute = route.offlineAsk;
  const failures = [];
  const positives = new Map([
    ['R01', ['roof', 'color']], ['R02', ['hood', 'color']], ['R03', ['roof', 'finish']],
    ['R04', ['roof', 'relative']], ['R14', ['roof', 'source-colour']], ['R15', ['right side', 'color']]
  ]);
  for (const item of oracle.cases) {
    resetCalls();
    const planned = E.plan(item.text, env);
    const shouldBePositive = positives.has(item.id);
    const expected = positives.get(item.id);
    if (expected) {
      const compiledRegion = item.id === 'R14' && planned && planned.kind === 'ops' ? E.compile(planned, env).zones[0].region : null;
      seedOwnedPart(expected[0], expected[1] === 'finish' ? 'base::gloss' : 'base::chrome', expected[1] === 'finish' ? '#1347a8' : '#f2c500', item.id === 'R14' && planned && planned.ops && planned.ops[0] ? planned.ops[0].target : null, compiledRegion);
    }
    else { route.zones = []; route._editReg = {}; route._editRegPendingBefore = {}; route._editRegSig = 'test-car'; }
    if (shouldBePositive && !(planned && planned.exactPart)) {
      const missed = await actualRoute(item.text, {});
      const exactQueuedPart = missed.queue && missed.queue.length === 1 && partFromQueue(missed.queue[0]) === expected[0];
      if (item.id === 'R14' && exactQueuedPart && isQueuedEdit(missed.queue[0])) {
        assert.equal(Object.hasOwn(missed.queue[0], 'finish'), false, 'source-colour correction must preserve the existing finish');
        assert.equal(missed.route, 'edit', 'source-colour correction must stay on the scoped editor route');
        const desired = E.compile(planned, env).zones[0];
        const transformFields = ['color', 'hue', 'saturation', 'brightness', 'spec_shift'].filter(k => Object.hasOwn(desired, k));
        const dropped = transformFields.filter(k => JSON.stringify(missed.queue[0][k]) !== JSON.stringify(desired[k]));
        if (dropped.length) failures.push(`${item.id} ${JSON.stringify(item.text)}: E.compile requested ${JSON.stringify(Object.fromEntries(transformFields.map(k => [k, desired[k]])))} but actual queue edit omitted/changed ${dropped.join(', ')}; queue=${JSON.stringify(missed.queue[0])}`);
      } else failures.push(`${item.id} ${JSON.stringify(item.text)}: expected exactPart; E.plan returned ${JSON.stringify(planned)}; actual route=${missed.route}, queued=${JSON.stringify(missed.queue && missed.queue.map(partFromQueue))}`);
      continue;
    }
    if (shouldBePositive) assert.equal(planned.exactPart, true, `${item.id}: expected one exact named-part operation`);
    else assert.notEqual(planned && planned.exactPart, true, `${item.id}: excluded/compound/advice text must not be exactPart`);

    const result = await actualRoute(item.text, {});
    if (expected) {
      assert.equal(result.route, 'edit', `${item.id}: exact part must win the real offlineAsk route`);
      assert.equal(result.queue.length, 1, `${item.id}: expected one queued panel operation`);
      assert.deepEqual([partFromQueue(result.queue[0])], [expected[0]], `${item.id}: actual queued target was not the named part`);
      assert.equal(route.coreCalls, 0, `${item.id}: should not be stolen by compound/advisor/core route`);
      if (expected[1] === 'color' || expected[1] === 'source-colour') {
        assert.ok(isQueuedEdit(result.queue[0]), `${item.id}: existing helper-owned panel should be reused`);
        assert.equal(Object.hasOwn(result.queue[0], 'finish'), false, `${item.id}: color-only edit must retain existing finish`);
      }
      if (expected[1] === 'finish') {
        assert.ok(isQueuedEdit(result.queue[0]), `${item.id}: existing helper-owned panel should be reused`);
        assert.equal(result.queue[0].finish, E.lookById('satin').found, `${item.id}: explicit finish must be queued`);
        assert.equal(Object.hasOwn(result.queue[0], 'color'), false, `${item.id}: finish-only edit must retain existing color`);
      }
      if (expected[1] === 'relative') {
        assert.ok(isQueuedEdit(result.queue[0]), `${item.id}: existing helper-owned panel should be reused`);
        assert.ok(result.queue[0].finish, `${item.id}: relative finish adjustment must produce a finish update`);
        assert.equal(Object.hasOwn(result.queue[0], 'color'), false, `${item.id}: relative finish adjustment must retain existing color`);
      }
    } else {
      const queueLength = result.queue ? result.queue.length : 0;
      if (item.id === 'R16') {
        assert.notEqual(planned && planned.exactPart, true, 'whole-body exception must not use the single-part owner');
        if (result.route === 'edit') {
          assert.equal((planned || {}).atomicScope, true, 'queued body-plus-part exception must remain atomic');
          assert.deepEqual(Array.from(result.queue, scopeFromQueue).sort(), ['body', 'hood'], 'body-plus-hood queue scope must be retained');
        } else assert.equal(queueLength, 0, 'unrecognized whole-body exception must not partially queue');
      } else if (queueLength) {
        failures.push(`${item.id} ${JSON.stringify(item.text)}: unsafe/advice/clarification route queued ${JSON.stringify(result.queue.map(partFromQueue))}`);
      }
      if (item.id === 'R13') assert.equal(result.route, 'edit-ask', 'protected hood must ask before mutation');
      if (['R05', 'R06', 'R07'].includes(item.id)) assert.equal(result.route, 'core', `${item.id}: guidance should stay out of the edit queue`);
      if (item.id === 'R11') assert.equal(result.route, 'core', `${item.id}: layer stack should not be claimed by the simple-part route`);
    }
  }

  // Post-oracle transform projection checks: offsets are sourced from real E.compile output,
  // then compared with the actual queued edit fields to cover hue, brightness and saturation.
  const transformCases = [
    { text: 'Change the blue on the roof to pale red.', fields: ['color', 'hue', 'brightness'] },
    { text: 'Make the blue on the roof lighter.', fields: ['color', 'saturation', 'brightness'] },
    { text: 'Make the blue on the roof less saturated.', fields: ['color', 'saturation'] },
    { text: 'Change the blue on the roof to dark blue.', fields: ['color', 'hue'], expectedHue: 0 }
  ];
  for (const item of transformCases) {
    resetCalls();
    const plan = E.plan(item.text, env);
    assert(plan && plan.kind === 'ops' && plan.ops.length === 1, `${item.text}: actual edit plan must exist`);
    const compiled = E.compile(plan, env), desired = compiled.zones[0];
    assert(desired && item.fields.some(field => Object.hasOwn(desired, field)), `${item.text}: E.compile must emit a transform`);
    if (Object.hasOwn(item, 'expectedHue')) assert.equal(desired.hue, item.expectedHue, `${item.text}: frozen zero-offset supplement must exercise numeric zero`);
    seedOwnedPart('roof', 'base::chrome', '#f2c500', plan.ops[0].target, desired.region);
    const result = await actualRoute(item.text, {});
    assert.equal(result.route, 'edit', `${item.text}: expected direct local edit route`);
    assert.equal(result.queue.length, 1, `${item.text}: expected one queue item`);
    assert.ok(isQueuedEdit(result.queue[0]), `${item.text}: existing part helper zone should be reused`);
    assert.equal(partFromQueue(result.queue[0]), 'roof', `${item.text}: queued transform must stay on roof`);
    for (const field of item.fields) {
      assert.ok(Object.hasOwn(desired, field), `${item.text}: fixture expects real compile field ${field}`);
      assert.deepEqual(JSON.parse(JSON.stringify(result.queue[0][field])), JSON.parse(JSON.stringify(desired[field])), `${item.text}: actual queue dropped/changed ${field}`);
    }
    assert.equal(Object.hasOwn(result.queue[0], 'finish'), false, `${item.text}: color adjustment must retain existing finish`);
  }

  // Post-oracle safety probes, added only after source inspection surfaced leading prohibitions.
  // These are intentionally separate from the frozen 16-case independent oracle.
  const prohibited = [
    'Do not make the roof red.',
    'Do not paint the hood red.',
    'Never repaint the passenger side gold.'
  ];
  for (const text of prohibited) {
    resetCalls(); route.zones = []; route._editReg = {}; route._editRegPendingBefore = {}; route._editRegSig = 'test-car';
    const p = E.plan(text, env);
    if (p && p.exactPart) failures.push(`POST-ORACLE prohibited request ${JSON.stringify(text)}: E.plan marked it exactPart`);
    const result = await actualRoute(text, {});
    if (result.queue && result.queue.length) failures.push(`POST-ORACLE prohibited request ${JSON.stringify(text)} queued ${JSON.stringify(result.queue.map(partFromQueue))}`);
  }

  // Two explicit panel targets may form a real compound, but may never become a single-part shortcut.
  const both = oracle.cases.find(x => x.id === 'R12');
  assert.notEqual((E.plan(both.text, env) || {}).exactPart, true);
  assert(D.compoundPlan(both.text), 'two-panel explicit request remains a designer-owned compound');
  const exception = oracle.cases.find(x => x.id === 'R16');
  const excPlan = E.plan(exception.text, env);
  assert.notEqual(excPlan && excPlan.exactPart, true, 'whole-body exception must not use the single-part route');

  // The actual configured/offline eligibility predicate remains true for the owned named-part edit in either setting.
  for (const configured of [false, true]) {
    route.configured = configured;
    for (const id of ['R01', 'R03', 'R04', 'R14', 'R15']) {
      const text = oracle.cases.find(x => x.id === id).text;
      assert.equal(route.offlineCanHandle(text), true, `${id}: exact named-part edit should remain eligible (configured=${configured})`);
    }
  }

  const hash = crypto.createHash('sha256').update(fs.readFileSync(path.join(root, 'js/spb-pro-ai.js'))).digest('hex').toUpperCase();
  if (failures.length) {
    console.error(`BLOCKED ai_named_part_route_review_contract.cjs (${failures.length} expected named-part routes not owned; pro-ai sha256 ${hash})`);
    failures.forEach(x => console.error(' - ' + x));
    process.exitCode = 1;
  } else console.log(`PASS ai_named_part_route_review_contract.cjs (16 frozen routes; 5 exactPart paths + 1 scoped source-colour path; 4 real hue/brightness/saturation queue supplements incl. zero hue; offline eligibility both settings; pro-ai sha256 ${hash})`);
})().catch(err => { console.error(err); process.exitCode = 1; });
