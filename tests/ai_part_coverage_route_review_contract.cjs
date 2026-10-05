'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');

const root = path.resolve(__dirname, '..');
const oraclePath = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_PART_COVERAGE_ROUTE_ORACLE_2026-10-03.json');
const oracleHash = 'CFA122C3B99ED6911E3E29D508F3E1A258EACF53CDFBA4F1B4DE81FFB30C6C56';
assert.equal(crypto.createHash('sha256').update(fs.readFileSync(oraclePath)).digest('hex').toUpperCase(), oracleHash, 'frozen W9 oracle changed');
const oracle = JSON.parse(fs.readFileSync(oraclePath, 'utf8'));

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
const D = w.SpbProDesign, E = w.SpbProEdit;
const env = { palette: [
  { hex: '#141416', share_pct: 52 }, { hex: '#f2c500', share_pct: 22 },
  { hex: '#f1f1ee', share_pct: 14 }, { hex: '#1347a8', share_pct: 5 }
], layers: [] };
const aiSource = fs.readFileSync(path.join(root, 'js/spb-pro-ai.js'), 'utf8');
const route = {
  window: Object.assign(w, { SpbMaterialControls: undefined, SpbProElements: undefined }), console, Promise,
  D, E, AI: { cached: () => ({ configured: !!route.configured }) },
  configured: false, _busy: false, _skipParts: true, _absent: {}, CAR: null,
  _offlineLast: null, _advLast: null, _advRejected: [], _advDislikes: [], _forcedIdeaCols: null,
  _reqText: '', _specOnlyReq: false, _beforeImg: null, _progress: '', _editReg: {}, _editRegPendingBefore: {}, _editRegSig: 'coverage-car', zones: [],
  coverageCalls: 0, editCalls: 0, coreCalls: 0, providerCalls: 0, supportCalls: 0, supportSendCalls: 0, finished: [], committedQueue: [],
  editPlan: text => E.plan(text, env),
  captureOriginal() {}, intentSpecOnly: () => false, editYieldsToStack: () => false,
  offlineLookAsk: () => Promise.resolve({ route: 'ask', queue: [] }), offlineEditAskFallback: () => Promise.resolve({ route: 'ask', queue: [] }),
  offlineRefineAsk: () => Promise.resolve({ route: 'ask', queue: [] }), offlineIdeasAsk: () => Promise.resolve({ route: 'ask', queue: [] }),
  offlineLayerVisAsk: () => Promise.resolve({ route: 'ask', queue: [] }), offlineElemWrong: () => Promise.resolve({ route: 'ask', queue: [] }),
  offlineSpecAsk: () => Promise.resolve({ route: 'ask', queue: [] }), offlinePartAsk: () => Promise.resolve({ route: 'ask', queue: [] }),
  offlineElementAsk: () => Promise.resolve({ route: 'ask', queue: [] }), offlineStartOver: () => ({ route: 'ask', queue: [] }), offlineUndo: () => ({ route: 'ask', queue: [] }),
  offlineHowto: () => null, preflightTeach: () => Promise.resolve({ route: 'ask', queue: [] }), planParts: () => [],
  elementRunCurrent: () => true, elementPaintChangedResult: () => ({ cancelled: true }),
  offlineFirst: () => true, selfHelpClaim: () => null, selfHelpResult: x => x,
  advisorIntent: () => null, advisorEnv: () => ({}), advisorReply() { throw new Error('advisor must not answer a covered edit'); },
  START_OVER_RE: /^\s*(?:start over|new design)\b/i, SMALL_HELLO_RE: /^\s*(hi|hello)\b/i, SMALL_THANKS_RE: /^\s*thanks\b/i,
  CANT_RE: /$a/, NUM_FIX_RE: /$a/, NOT_ELEM_RE: /$a/, layerVisRequest: () => null, lookEntry: () => null,
  offlineCannot: () => null, offlineHowtoPeek: () => false, offlineScopeReply: () => ({ text: 'No change.' }),
  warm: () => Promise.resolve(), render() {}, prepEnv: () => Promise.resolve(env), resolveLook: () => Promise.resolve(null), elementKinds: () => [],
  exclTargets: () => [], markPartFollowupQueue() {}, editOverlapNote: () => '', editOverlapKinds: () => [], exclNotes: () => [],
  _panel: null, _log: [], TEACH_RE: /never-match-z0/, QUESTION_RE: /$a/, CHECK_AGAIN_RE: /$a/,
  elemCurrentCard: () => null, elementPaintSig: () => '', elementRunIdentity: () => null,
  elemReplyAction: () => null, runElemAction: () => false, elemOwnsText: () => false,
  supportClass() { route.supportCalls++; return { kind: 'faq' }; }, supportSend() { route.supportSendCalls++; return true; },
  finish(result) { route.finished.push(result); },
  carSig: () => 'coverage-car', partRegHas: (obj, key) => Object.prototype.hasOwnProperty.call(obj || {}, key),
  _gen: 0, _snapGen: 0, _activeId: null, RECENT: [], _advUsed: null,
  applySnapshots: [], undoZoneChange() { const snap = route.applySnapshots.pop(); if (snap) route.zones = JSON.parse(JSON.stringify(snap)); },
  renderZones() {}, triggerPreviewRender() {},
  normaliseSpec: spec => spec, protectDecals() {}, friendlyZoneError: msg => String(msg || ''),
  editPlural: label => /(numbers|sponsors|stripes|logos|decals|lines|bands|accents|panels|parts|bumpers)$/.test(String(label)),
  failPart: null, addCalls: [], editQueueCalls: [],
  makeTools(queue) { return [
    { name: 'add_zone', handler(spec) {
      const part = spec.region && spec.region.part;
      if (route.failPart && part === route.failPart) return { error: 'unknown part: ' + part };
      const item = { kind: 'add', spec: JSON.parse(JSON.stringify(spec)) };
      queue.push(item); route.committedQueue.push(item); return {};
    } },
    { name: 'edit_zone', handler(args) {
      const copiedArgs = JSON.parse(JSON.stringify(args));
      const spec = {}; Object.keys(copiedArgs).forEach(k => { if (!['zone', 'zone_id', 'zone_name', 'expect_name', '_spbPartRegKey', '_spbPartOwnerName', '_spbPartForgetKey'].includes(k)) spec[k] = copiedArgs[k]; });
      const item = { kind: 'edit', zone: Number(copiedArgs.zone) || 0, spec, _spbPartRegKey: copiedArgs._spbPartRegKey || null, _spbPartOwnerName: copiedArgs._spbPartOwnerName || null, args: copiedArgs };
      queue.push(item); route.committedQueue.push(item); route.editQueueCalls.push(item); return {};
    } }
  ]; },
  editReply(text, chips, options) { return { route: options && options.queue ? 'edit' : 'ask', text, chips: chips || [], queue: options && options.queue ? options.queue : [], tools: options && options.tools || [] }; },
  askCore() { route.providerCalls++; return Promise.resolve({ route: 'provider', queue: [], calls: 1 }); }
};
route.window.SpbProElements = undefined; route.window.SpbMaterialControls = undefined;
vm.createContext(route);
for (const name of [
  'partRegionKey', 'editKey', 'editPlural', 'offlineMaterialPlan', 'queueEditZones',
  'offlineCoveredPartAsk', 'offlineEditAsk', 'offlineCanHandle', 'offlineAsk', 'offlineAskCore',
  'partRegistryState', 'partOwnerCurrent', 'registerAppliedPartZones', 'reconcilePartRegistry', 'clearPartRegistryPending',
  'applyQueue', 'restorePartRegistryUndo', 'doUndo', 'ask'
]) vm.runInContext(extractFunction(aiSource, name), route, { filename: `js/spb-pro-ai.js#${name}` });

// The native batch implementation is the only effect mocked here. The actual
// applyQueue and doUndo orchestration below is exercised against this adapter.
route.Z = { batch(ops) {
  route.applySnapshots.push(JSON.parse(JSON.stringify(route.zones)));
  return ops.map(op => {
    const z = route.zones[op.zone];
    if (!z || op.kind !== 'edit') return { ok: false, applied: [], warnings: ['missing mock target'], index: op.zone };
    const spec = JSON.parse(JSON.stringify(op.spec || {}));
    Object.keys(spec).forEach(k => { if (k === 'color') z.colour = spec[k]; else z[k] = spec[k]; });
    return { ok: true, applied: Object.keys(op.spec || {}), index: op.zone, name: z.name };
  }); },
  quiet(fn) { return fn(); }, catchAll() { return false; }
};

// Count the real covered-part handler invocation without replacing its body.
route._offlineCoveredPartAsk = route.offlineCoveredPartAsk;
route.offlineCoveredPartAsk = function (text, proof, options) {
  route.coverageCalls++;
  return route._offlineCoveredPartAsk(text, proof, options);
};

const hashMask = mask => { let h = 2166136261; for (const b of mask) h = Math.imul(h ^ (Number(b) & 255), 16777619); return mask.length + ':' + (h >>> 0).toString(36); };
function seedOwnedPart(part, finish, color, regionOverride) {
  const region = regionOverride || { part }, key = route.editKey(region), name = `Existing owned ${part} finish`;
  const mask = new Uint8Array([11, 22, 33]);
  route.zones = [{ id: `z-${part}`, name, muted: false, regionMask: mask, useRegion: true,
    finishKey: finish, colour: color, _aiPartProv: { r: JSON.stringify(region), z: hashMask(mask), l: '', e: '' } }];
  route._editReg = { [key]: name }; route._editRegPendingBefore = {}; route._editRegSig = 'coverage-car';
}
function clearState() {
  route.zones = []; route._editReg = {}; route._editRegPendingBefore = {}; route._editRegSig = 'coverage-car';
  route.failPart = null; route.committedQueue = []; route.addCalls = []; route.editQueueCalls = []; route.applySnapshots = [];
  route._offlineLast = null; route._advLast = null; route._busy = false;
}
function queuedParts(result) {
  return Array.from(result.queue || [], q => q.kind === 'add' ? q.spec.region && q.spec.region.part : JSON.parse(q.args._spbPartRegKey || '{}').p);
}

(async () => {
  const actualCases = [...oracle.fresh_cases, ...oracle.supplied_original_frozen_cases];
  assert.equal(oracle.fresh_cases.length, 14); assert.equal(oracle.supplied_original_frozen_cases.length, 2);
  const results = {};
  for (const item of actualCases) {
    clearState();
    const proof = D.offlinePartCoverage(item.text);
    route.configured = false;
    const result = await route.offlineAsk(item.text, {});
    results[item.id] = { proof, result };
    assert(result && typeof result === 'object', `${item.id}: route returns a local response`);
  }

  // Post-freeze regression supplement requested by the owner of the D-helper fix.
  // These punctuation-separated later assignments must not be swallowed by a
  // preservation tail. They were added after the frozen 14-case oracle.
  const punctuationCases = [
    'Make the hood red. Leave all other panels alone. Make the roof blue.',
    'Make the hood red, leave all other panels alone; make the roof blue.',
    'Make the hood red, keep all other panels unchanged, paint the roof blue.'
  ];
  const punctuationOutcomes = [];
  for (const text of punctuationCases) {
    clearState(); route.configured = false;
    const proof = D.offlinePartCoverage(text);
    const result = await route.offlineAsk(text, {});
    const parts = queuedParts(result).sort();
    punctuationOutcomes.push({ text, proofComplete: !!(proof && proof.complete), proofParts: proof && proof.zones ? Array.from(proof.zones, z => z.region && z.region.part).sort() : [], route: result && result.route || 'ask', parts, textReply: result && result.text });
  }
  for (const [i, outcome] of punctuationOutcomes.entries()) {
    assert.equal(outcome.proofComplete, true, `post-freeze punctuation case ${i + 1} must preserve both requested jobs`);
    assert.equal(outcome.route, 'edit', `post-freeze punctuation case ${i + 1} must complete through actual coverage route`);
    assert.deepEqual(outcome.proofParts, ['hood', 'roof']);
    assert.deepEqual(outcome.parts, ['hood', 'roof']);
  }

  // A normal layered compound should keep the material stack and named-part
  // scope. The local route may ask if catalogue resolution is required; it must
  // not misrepresent the request as a body recolor.
  const stackText = 'Make only the hood matte black base with silver pearl flakes on top.';
  clearState();
  const stackCoverage = D.offlinePartCoverage(stackText);
  const stackPlan = D.compoundPlan(stackText);
  const stackRoute = await route.offlineAsk(stackText, {});
  const stackDiagnostic = {
    coverageClaimed: !!(stackCoverage && stackCoverage.complete),
    compound: stackPlan && { zones: stackPlan.zones && stackPlan.zones.map(z => ({ part: z.region && z.region.part, layers: z.layers, finish: z.finish, color: z.color })), text: stackPlan.text },
    route: stackRoute && stackRoute.route || 'ask', parts: queuedParts(stackRoute || {}).sort(), text: stackRoute && stackRoute.text
  };
  assert.equal(stackDiagnostic.coverageClaimed, false, 'layered stack request must not be misclaimed by simple-part coverage');
  assert.deepEqual(stackDiagnostic.parts, [], 'unresolved layered stack remains unapplied rather than partially applying the base');

  // The original accepted requests must take the proof route and queue all requested parts.
  for (const item of oracle.supplied_original_frozen_cases) {
    const { proof, result } = results[item.id];
    assert(proof && proof.complete, `${item.id}: frozen accepted long request has full coverage proof`);
    assert.equal(result.route, 'edit', `${item.id}: actual offlineAsk must complete locally`);
    const parts = queuedParts(result).sort();
    assert.deepEqual(parts, item.id === 'W9-O01' ? ['hood'] : ['hood', 'roof'], `${item.id}: returned queued parts must match request exactly`);
    assert(parts.every(p => p && !['body', 'whole car'].includes(p)), `${item.id}: no implicit body zone`);
    const calls = route.committedQueue.map(q => q.kind === 'add' ? q.spec : q.args);
    for (const q of calls) assert.ok((q._spbPartRegKey || '').length || item.id === 'W9-O01' || q.region && q.region.part, `${item.id}: queued edit must retain part scope`);
  }

  // Configured and unconfigured ask() routes both use the proof when offline-first is enabled.
  for (const configured of [false, true]) {
    clearState(); route.configured = configured;
    const result = await route.ask(oracle.supplied_original_frozen_cases[0].text, {});
    assert.equal(result.route, 'edit', `ask configured=${configured} should use the complete local coverage route`);
    assert.equal(route.providerCalls, 0, `ask configured=${configured} should not call provider for covered request`);
    assert.deepEqual(queuedParts(result), ['hood']);
  }

  // The existing roof finish must survive a color-only request. The current chrome owner is reused.
  const colorOnly = oracle.fresh_cases.find(x => x.id === 'W9-F07');
  clearState();
  const colorPlan = E.plan(colorOnly.text, env);
  const roofRegion = colorPlan && colorPlan.ops && colorPlan.ops[0] && colorPlan.ops[0].region;
  seedOwnedPart('roof', 'base::chrome', '#141416', roofRegion);
  const compiledColor = E.compile(colorPlan, env);
  assert.equal(compiledColor.ask, null, 'actual editor compile resolves the color-only owned-roof request');
  assert.equal(compiledColor.zones.length, 1);
  assert.equal(compiledColor.zones[0].region.part, 'roof', 'compiled color-only edit remains roof-scoped');
  const colorResult = await route.offlineAsk(colorOnly.text, {});
  const colorOnlyActual = { planKind: colorPlan && colorPlan.kind, route: colorResult && colorResult.route, text: colorResult && colorResult.text, queue: colorResult && colorResult.queue };
  let colorApplyUndoActual = null;
  if (colorResult && colorResult.route === 'edit') {
    assert.equal(colorResult.queue.length, 1);
    assert.equal(colorResult.queue[0].kind, 'edit');
    assert.equal(Object.hasOwn(colorResult.queue[0].spec, 'finish'), false, 'color-only update must preserve current chrome finish');
    assert.equal(colorResult.queue[0].spec.color, colorPlan.ops[0].colour.hex, 'color-only update must queue parsed destination');
    const applied = route.applyQueue(colorResult.queue, 'W9 owned roof color only', false);
    assert.equal(applied.failed.length, 0, 'actual applyQueue accepts the owned part edit');
    assert.equal(route.zones[0].colour, colorPlan.ops[0].colour.hex, 'mocked native batch receives the queued destination');
    assert.equal(route.zones[0].finishKey, 'base::chrome', 'applying color-only queue retains the owned chrome finish');
    assert.equal(route._editReg[route.editKey({ part: 'roof' })], colorResult.queue[0].spec.name, 'apply advances registry ownership to the renamed edited zone');
    const appliedState = { colour: route.zones[0].colour, finish: route.zones[0].finishKey, owner: route._editReg[route.editKey({ part: 'roof' })] };
    route._advRejected = [];
    const undoEntry = { undoable: true, zoneUndo: true, _partRegUndo: applied.partRegUndo, request: colorOnly.text };
    route.doUndo(undoEntry);
    assert.equal(undoEntry.undone, true, 'actual doUndo marks the applied edit undone');
    assert.equal(route.zones[0].colour, '#141416', 'actual doUndo orchestration restores the prior roof color');
    assert.equal(route.zones[0].finishKey, 'base::chrome', 'Undo preserves the original chrome finish');
    assert.equal(route._editReg[route.editKey({ part: 'roof' })], 'Existing owned roof finish', 'Undo retains the prior part owner');
    colorApplyUndoActual = {
      compile: { ask: compiledColor.ask, zones: Array.from(compiledColor.zones, z => ({ part: z.region && z.region.part, color: z.color, finish: z.finish })) },
      queued: { kind: colorResult.queue[0].kind, partKey: colorResult.queue[0]._spbPartRegKey, spec: colorResult.queue[0].spec },
      apply: { failed: applied.failed, state: appliedState, undoMetadataPresent: !!applied.partRegUndo },
      undo: { undone: undoEntry.undone, colour: route.zones[0].colour, finish: route.zones[0].finishKey, owner: route._editReg[route.editKey({ part: 'roof' })] }
    };
  } else {
    // Preserve the exact reproduction in the machine report; do not convert a
    // missing owned-part route into a pass merely because it avoided mutation.
    results['W9-F07-OWNED-ROOF'] = colorOnlyActual;
  }

  // OfflineAskCore must have the same coverage priority as offlineAsk.
  clearState();
  const coreResult = await route.offlineAskCore(oracle.supplied_original_frozen_cases[1].text, {});
  assert.equal(coreResult.route, 'edit');
  assert.deepEqual(queuedParts(coreResult).sort(), ['hood', 'roof']);

  // A failed add on one requested part returns no queue and leaves ownership/state unchanged.
  clearState(); route.failPart = 'roof';
  const before = JSON.stringify({ zones: route.zones, registry: route._editReg, pending: route._editRegPendingBefore });
  const failure = await route.offlineAsk(oracle.supplied_original_frozen_cases[1].text, {});
  assert.notEqual(failure.route, 'edit', 'one failed requested target must not be reported as complete');
  assert.equal(failure.queue.length, 0, 'a failed target suppresses the whole returned queue');
  assert.equal(JSON.stringify({ zones: route.zones, registry: route._editReg, pending: route._editRegPendingBefore }), before, 'failure must not alter zone or part-owner registry state');

  // An invalid member in a multi-target request cannot allow the known member to apply alone.
  const invalidMix = 'Make the roof red and the windshield gold, while leaving the rest unchanged.';
  clearState();
  const invalidProof = D.offlinePartCoverage(invalidMix);
  const invalidResult = await route.offlineAsk(invalidMix, {});
  assert(!invalidProof || !invalidProof.complete, 'unsupported windshield target must not receive a coverage proof');
  assert.equal(invalidResult.queue.length || 0, 0, 'invalid mixed target must not queue the valid roof as a partial edit');

  // Check full-text offline eligibility, send ownership, and routing negatives.
  for (const item of oracle.fresh_cases.filter(x => ['W9-F11', 'W9-F12', 'W9-F13', 'W9-F14'].includes(x.id))) {
    clearState();
    const result = await route.offlineAsk(item.text, {});
    assert.equal(result.queue.length || 0, 0, `${item.id}: unsupported/prohibition/advice request must not queue`);
  }
  for (const configured of [false, true]) {
    route.configured = configured;
    assert.equal(route.offlineCanHandle(oracle.supplied_original_frozen_cases[0].text), true, `coverage eligibility must hold configured=${configured}`);
  }
  // send() is verified by its source eligibility expression below; the full UI event
  // handler is deliberately excluded because it owns DOM/native UI effects.
  assert.match(aiSource, /_covered0\s*=\s*D\s*&&\s*D\.offlinePartCoverage\s*\?\s*D\.offlinePartCoverage\(text\)\s*:\s*null/);
  assert(aiSource.includes('_covered0 || (!(window.SpbSupport'), 'send has a dedicated covered-request offline gate');

  const actualCovered = actualCases.filter(x => results[x.id].proof && results[x.id].proof.complete).map(x => x.id);
  const observed = Object.fromEntries(actualCases.map(x => [x.id, {
    proof: !!(results[x.id].proof && results[x.id].proof.complete),
    route: results[x.id].result && results[x.id].result.route || 'ask',
    parts: queuedParts(results[x.id].result || {}).sort(),
    text: results[x.id].result && results[x.id].result.text || ''
  }]));
  const sourceHashes = {};
  for (const f of ['js/spb-pro-ai.js', 'js/spb-pro-edit.js', 'js/spb-pro-design.js']) sourceHashes[f] = crypto.createHash('sha256').update(fs.readFileSync(path.join(root, f))).digest('hex').toUpperCase();
  const blockers = [];
  if (colorOnlyActual.route !== 'edit') blockers.push({ id: 'W9-F07-OWNED-ROOF', request: colorOnly.text, actual: colorOnlyActual, expected: 'queue one roof color-only edit preserving existing base::chrome' });
  const report = {
    review: 'W9 actual long-part coverage route review', date: '2026-10-04', status: blockers.length ? 'BLOCKED' : 'PASS',
    oracle: { path: 'docs/handoff_reports/AI_HELPER_14H_PART_COVERAGE_ROUTE_ORACLE_2026-10-03.json', sha256: oracleHash, fresh_cases: oracle.fresh_cases.length, supplied_original_frozen_cases: oracle.supplied_original_frozen_cases.length },
    production_hashes_sha256: sourceHashes,
    checks: {
      original_requests: { passed: 2, expected: 2, routes: observed },
      configured_ask_false_true: 'PASS', offlineAskCore_original_two_part: 'PASS',
      punctuation_supplement: { passed: punctuationOutcomes.length, outcomes: punctuationOutcomes },
      failed_target_atomicity: 'PASS: roof add error returned no queue; zone and ownership registries unchanged',
      unsupported_mixed_target: 'PASS: windshield+roof did not receive complete coverage proof and queued no partial edit',
      prohibition_advice_unknown_extra: 'PASS: no queued mutations',
      layered_stack: stackDiagnostic,
      owned_chrome_color_only: colorApplyUndoActual || colorOnlyActual
    }, blockers,
    before_after: {
      before_W12: { status: 'BLOCKED', editor_sha256: 'FD2E2365F45A9DD2751C6EB6701BFD78CFD57C3230D8CB999842AA5FADD79AC2', F07: { planKind: null, route: 'No change.', queued: false } },
      after_W12: { status: colorApplyUndoActual ? 'PASS' : 'BLOCKED', editor_sha256: sourceHashes['js/spb-pro-edit.js'], F07: colorApplyUndoActual || colorOnlyActual }
    },
    limits: ['No browser/native app or provider call was run. Actual production compile, offline route, queueEditZones, applyQueue, and doUndo orchestration were exercised; only the native Z.batch mutation and undoZoneChange effects were mocked.', 'offlineCanHandle was invoked directly for configured true/false; full send DOM handler was not executed. Its covered-request gate was source-checked.', 'The 14 fresh cases are independently frozen; actual outcome text/queue is recorded per case. Only the two supplied accepted long prompts and three post-freeze punctuation supplements are asserted as completed coverage.', 'Layered material request is conservative incomplete support: coverage does not claim it; compound omits the pearl layer, while the actual route asks and queues nothing. This is a capability gap, not an unsafe mutation.']
  };
  const reportPath = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_PART_COVERAGE_ROUTE_REVIEW_2026-10-03.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: report.status, blockers, originalAccepted: 2, punctuationPassed: punctuationOutcomes.length, sourceHashes }, null, 2));
  if (blockers.length) process.exitCode = 2;
})().catch(err => { console.error(err); process.exitCode = 1; });
