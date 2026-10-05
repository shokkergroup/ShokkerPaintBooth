/* W37 fresh oracle, frozen before source inspection. Keep expected outcomes separate
   from the producer's W34 fixtures. The harness below must use frozen candidate bytes. */
'use strict';
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.resolve(__dirname, '..');
const FROZEN = path.join(ROOT, '_easy_claude_work', 'ai14h_w37_frozen', 'js');
const ORACLE = Object.freeze([
  { id: 'matte-black-carbon-keep-paint', request: 'Make the roof matte black with gold carbon overlay, but keep its current paint color.', expected: 'ask_no_queue' },
  { id: 'chrome-finish-keep-red', request: 'Make only the roof chrome and keep its current red paint color.', expected: 'execute_roof_finish_only' },
  { id: 'chrome-finish-keep-navy', request: 'Make the hood chrome but leave its current navy paint alone.', expected: 'execute_hood_finish_only' },
  { id: 'roof-red-keep-sponsors', request: 'Make the roof red and keep the sponsors unchanged.', expected: 'execute_roof_only' },
  { id: 'quoted-preservation-phrase', request: 'My notes say “keep the hood unchanged”; paint the roof red.', expected: 'execute_roof_only' },
  { id: 'howto-question', request: 'How do I keep the hood unchanged while painting the roof red?', expected: 'help_no_queue' },
  { id: 'separate-part-color-facets', request: 'Make the roof gold and keep the hood navy.', expected: 'execute_roof_gold_and_hood_navy' },
  { id: 'finish-stack-keep-current', request: 'Put a matte black base and gold carbon overlay on only the roof; keep its current paint color.', expected: 'ask_no_queue' },
  { id: 'finish-stack-no-contradiction', request: 'Make only the roof matte black with a gold carbon overlay.', expected: 'execute_roof_base_and_overlay' },
  { id: 'single-part-preserve-other', request: 'Paint the roof gold and leave the hood color as it is.', expected: 'execute_roof_only' },
  { id: 'advice-not-application', request: 'Would a gold carbon overlay work over the roof’s existing red paint?', expected: 'help_no_queue' },
  { id: 'explicit-unrelated-instruction', request: 'Keep all sponsor decals unchanged, then make only the roof deep red.', expected: 'execute_roof_only' }
]);
const ORACLE_SHA256 = '5ED699B9AFD0833874F30E9B6ECF3ABE19DAFFE49A032BECDC7BD227A3BEF42E';
const actualOracleHash = crypto.createHash('sha256').update(JSON.stringify(ORACLE) + '\n').digest('hex').toUpperCase();
if (actualOracleHash !== ORACLE_SHA256) throw new Error('W37 oracle changed: ' + actualOracleHash);

const INPUT_HASHES = Object.freeze({
  guard: '9931DA531D064B8F32F2CF4B1BFA7F03D0A42DC6E0CAD698DBD6B9E94CE02C84',
  proAI: '39FBB9A1CBB421347763BA78B6D8E3E0307B082A2DB42B09DE0D8AC705BEAF9A',
  design: '0533393FF5F2170236F60D4ED489C7AE52F98805E12B0764DA67A967F756F2E8',
  edit: 'D940E6688B3ED5E8FA0514C8774E73A4A2B564AD723E507166248E3E97AC75D0'
});
function readPinned(file, expected) {
  const b = fs.readFileSync(file), got = crypto.createHash('sha256').update(b).digest('hex').toUpperCase();
  assert.equal(got, expected, path.basename(file) + ' frozen input changed'); return b.toString('utf8');
}
function extractFunction(src, name) {
  const start = src.indexOf(`function ${name}(`); assert(start >= 0, 'missing actual function ' + name);
  const brace = src.indexOf('{', start); let depth = 0, quote = null, line = false, block = false, esc = false;
  for (let i = brace; i < src.length; i++) {
    const c = src[i], n = src[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (quote) { if (esc) { esc = false; continue; } if (c === '\\') { esc = true; continue; } if (c === quote) quote = null; continue; }
    if (c === '/' && n === '/') { line = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    if (c === '}' && --depth === 0) return src.slice(start, i + 1);
  }
  throw new Error('unterminated function ' + name);
}
function frozenRoute() {
  const dir = path.join(ROOT, '_easy_claude_work', 'ai14h_w34_sources', 'js');
  const candidateAI = readPinned(path.join(FROZEN, 'spb-pro-ai.js'), INPUT_HASHES.proAI);
  const guard = readPinned(path.join(FROZEN, 'spb-ai-complete-instruction-guard.js'), INPUT_HASHES.guard);
  const design = readPinned(path.join(dir, 'spb-pro-design.js'), INPUT_HASHES.design);
  const edit = readPinned(path.join(dir, 'spb-pro-edit.js'), INPUT_HASHES.edit);
  const w = { console, Promise, document: {} }; w.window = w; vm.createContext(w);
  vm.runInContext(design, w, { filename: 'frozen W34 designer' });
  vm.runInContext(edit, w, { filename: 'frozen W34 edit planner' });
  vm.runInContext(guard, w, { filename: 'frozen W34 guard' });
  const D = w.SpbProDesign, E = w.SpbProEdit;
  const env = { palette: [{ hex: '#141416', share_pct: 52 }, { hex: '#f2c500', share_pct: 22 }, { hex: '#f1f1ee', share_pct: 14 }, { hex: '#1347a8', share_pct: 5 }], layers: [] };
  const route = {
    window: w, console, Promise, D, E, AI: { cached: () => ({ configured: false }) },
    _busy: false, _skipParts: true, _absent: {}, CAR: null, _offlineLast: null, _advLast: null,
    _advRejected: [], _advDislikes: [], _forcedIdeaCols: null, _reqText: '', _specOnlyReq: false,
    _beforeImg: null, _progress: '', _editReg: {}, _editRegPendingBefore: {}, _editRegSig: 'car',
    zones: [], _log: [], _progAI: false, _progT0: 0, _progK: 0, _progEnd: 0, _panel: null,
    elementRunCurrent: () => true, elementPaintChangedResult: () => ({ cancelled: true }),
    editPlan: text => E.plan(text, env), offlineFirst: () => true, selfHelpClaim: text => (/^(How do I|How can|Would a gold)/i.test(text) ? { intent: 'help' } : null),
    selfHelpResult: value => ({ offline: true, text: 'help', queue: [], answer: value.intent }),
    offlineCanHandle: () => true, offlineGaveUp: () => false, logMiss() {}, render() {},
    askCore(text) { route.providerBoundaryCalls++; return Promise.resolve({ error: { message: 'provider stub only' }, queue: [] }); },
    offlineAskCore() { route.coreCalls++; return Promise.resolve({ offline: true, text: 'provider boundary', queue: [{ kind: 'should-not-run' }] }); },
    offlineInstructionPreflight: null, _preflightFallbackCalls: 0, coreCalls: 0, fallbackCalls: 0,
    finish(r, text) { route.finished = { r, text }; },
    offlineEditAsk(text, ed) { route.editCalls.push({ text, ed }); return Promise.resolve({ offline: true, text: 'captured local edit route', queue: [], editPlan: ed }); },
    offlineCoveredPartAsk(text, proof) { route.coveredCalls.push({ text, proof }); return Promise.resolve({ offline: true, text: 'captured part route', queue: [], proof }); },
    offlineElementAsk(text, intent) { route.elementCalls.push({ text, intent }); return Promise.resolve({ offline: true, text: 'captured element route', queue: [] }); },
    offlinePartAsk(text, intent) { route.partCalls.push({ text, intent }); return Promise.resolve({ offline: true, text: 'captured part fallback', queue: [] }); },
    offlineSpecAsk(text, intent) { route.specCalls.push({ text, intent }); return Promise.resolve({ offline: true, text: 'captured spec fallback', queue: [] }); },
    offlineScopeReply: () => ({ offline: true, text: 'scope ask', queue: [] }),
    offlineHowto: () => null, offlineStartOver: () => ({ queue: [] }), offlineUndo: () => ({ queue: [] }),
    captureOriginal() {}, intentSpecOnly: () => false, advisorOwns: () => false,
    elemCurrentCard: () => null, elementPaintSig: () => '', elementRunIdentity: () => null,
    elemReplyAction: () => null, runElemAction: () => false, complaintChip: () => false,
    complaintOf: () => null, offlineComplaint: () => null, selfHelpSig: () => '',
    offlineMaterialPlan: () => null, advisorIntent: () => null, layerVisRequest: () => null,
    offlineCannot: () => null, NUM_FIX_RE: /$a/, NOT_ELEM_RE: /$a/, TEACH_RE: /$a/,
    QUESTION_RE: /^how\b/i, CHECK_AGAIN_RE: /$a/, START_OVER_RE: /^$a/, CANT_RE: /^$a/,
    SMALL_HELLO_RE: /$a/, SMALL_THANKS_RE: /$a/, editCalls: [], coveredCalls: [], elementCalls: [], partCalls: [], specCalls: [], providerBoundaryCalls: 0,
    AI_cachedConfigured: false
  };
  Object.assign(w, route); w.window = w; vm.createContext(route);
  for (const name of ['offlineInstructionPreflight', 'offlineAsk', 'offlineAskCore', 'offlineLookAsk', 'editYieldsToStack', 'offlineCanHandle', 'ask']) {
    vm.runInContext(extractFunction(candidateAI, name), route, { filename: 'W34 candidate proAI#' + name });
  }
  const sendStart = candidateAI.indexOf('function send(text, o) {');
  const sendGuard = candidateAI.indexOf("var guarded = offlineInstructionPreflight(text); if (guarded) { finish(guarded, text, 'ask'); return; }", sendStart);
  assert(sendStart >= 0 && sendGuard > sendStart, 'actual send() preflight hook missing');
  vm.runInContext(candidateAI.slice(sendStart, sendGuard) + "var guarded = offlineInstructionPreflight(text); if (guarded) { finish(guarded, text, 'ask'); return; }\n}", route, { filename: 'W34 candidate proAI#send-through-preflight' });
  return { w, route, D, E, env, candidateAI };
}

async function main() {
  const { w, route, E } = frozenRoute();
  const guarded = new Set(['matte-black-carbon-keep-paint', 'finish-stack-keep-current']);
  const decisions = ORACLE.map(c => ({ id: c.id, decision: w.SpbAICompleteGuard.inspect(c.request), expected: c.expected }));
  const guardMismatches = decisions.filter(row => !!row.decision !== guarded.has(row.id));
  const actualResults = [];
  async function resultFrom(fn) { const r = await fn(); assert(r && Array.isArray(r.queue), 'route did not return a queue'); return r; }
  // Guarded requests stop at actual route boundaries with both configuration states.
  route.AI.cached = () => ({ configured: false });
  actualResults.push({ route: 'offlineAskCore/config-off', id: ORACLE[0].id, result: await resultFrom(() => route.offlineAskCore(ORACLE[0].request, {})) });
  route.AI.cached = () => ({ configured: true });
  actualResults.push({ route: 'ask/config-on', id: ORACLE[0].id, result: await resultFrom(() => route.ask(ORACLE[0].request, {})) });
  route.AI.cached = () => ({ configured: false });
  actualResults.push({ route: 'send/config-off', id: ORACLE[0].id, result: (route.send(ORACLE[0].request, {}), route.finished.r) });
  route.AI.cached = () => ({ configured: true });
  actualResults.push({ route: 'offlineLookAsk/config-on', id: ORACLE[0].id, result: await resultFrom(() => route.offlineLookAsk(ORACLE[0].request, { query: 'gold carbon overlay' }, {})) });
  for (const row of actualResults) { assert.equal(row.result.queue.length, 0, row.route + ' queued guarded request'); assert.equal(row.result.instructionGuard, 'preserved-paint-with-overlay'); }
  assert.equal(route.coreCalls, 0, 'guarded ask leaked to provider/core boundary');

  // Safe ordinary requests must pass the guard and reach the real typed edit planner.
  const positiveIds = ['chrome-finish-keep-red', 'chrome-finish-keep-navy', 'roof-red-keep-sponsors', 'quoted-preservation-phrase', 'separate-part-color-facets', 'finish-stack-no-contradiction', 'single-part-preserve-other', 'explicit-unrelated-instruction'];
  const positives = [];
  for (const id of positiveIds) {
    const c = ORACLE.find(x => x.id === id); route.AI.cached = () => ({ configured: false }); route._busy = false; route.editCalls.length = 0; route.coveredCalls.length = 0;
    const pre = route.offlineInstructionPreflight(c.request); assert.equal(pre, null, id + ' was blocked by guard');
    const r = await route.ask(c.request, {});
    positives.push({ id, result: r, edit: route.editCalls[0] && route.editCalls[0].ed, covered: route.coveredCalls[0] && route.coveredCalls[0].proof });
  }
  const roofFinish = positives.find(x => x.id === 'chrome-finish-keep-red');
  assert(roofFinish.edit && roofFinish.edit.kind === 'ops', 'roof finish-only phrase did not reach part edit owner');
  assert.equal(roofFinish.edit.ops[0].target.part, 'roof'); assert.equal(roofFinish.edit.ops[0].colour, null); assert.equal(roofFinish.edit.unknown.length, 0);
  const hoodFinish = positives.find(x => x.id === 'chrome-finish-keep-navy');
  assert(hoodFinish.edit && hoodFinish.edit.kind === 'ops', 'hood finish-only phrase did not reach part edit owner');
  // Mark safety/coverage honestly: an ask/no-queue is safe, but is not a completed supported edit.
  const outcomes = positives.map(x => ({ id: x.id, queueLength: x.result && x.result.queue ? x.result.queue.length : null, editKind: x.edit && x.edit.kind || null,
    unknown: x.edit && x.edit.unknown || null, protectedParts: x.edit && x.edit.protected_parts || null,
    planOps: x.edit && x.edit.ops ? x.edit.ops.map(op => ({ target: op.target, color: op.colour, finish: op.look && op.look.id, exclude: op.exclude })) : null,
    coverage: x.covered ? x.covered.status || x.covered.complete : null }));
  // Verify the concrete ask boundary for the missed put/overlay formulation.
  route.AI.cached = () => ({ configured: true });
  const missed = await route.ask(ORACLE[7].request, {});
  assert.equal(route.providerBoundaryCalls, 1, 'the unguarded fresh compound request did not reach the controlled provider boundary');
  const unsafeOrIncomplete = guardMismatches.length > 0 || positives.some(x => !x.edit || x.edit.kind === 'ask' || (x.edit.unknown && x.edit.unknown.length));
  console.log(JSON.stringify({ ok: !unsafeOrIncomplete, status: unsafeOrIncomplete ? 'BLOCKED' : 'PASS', oracleSha256: ORACLE_SHA256, cases: ORACLE.length, guardMismatches: guardMismatches.map(x => ({ id: x.id, expectedGuard: guarded.has(x.id), actualGuard: !!x.decision, decision: x.decision })), guardClassifications: decisions.map(x => ({ id: x.id, blocked: !!x.decision, reason: x.decision && x.decision.reason || null })), routes: actualResults.map(x => ({ route: x.route, id: x.id, queue: x.result.queue.length, calls: x.result.calls, model: x.result.model, guard: x.result.instructionGuard })), positiveRoutes: outcomes, unguardedCompoundBoundary: { id: ORACLE[7].id, queue: missed.queue && missed.queue.length, error: missed.error && missed.error.message, crossedProviderStub: route.providerBoundaryCalls === 1, note: 'ask() and offlineCanHandle() are source-extracted; provider call is a controlled stub, not a live call' }, providerOrCoreCalls: route.coreCalls, hashes: INPUT_HASHES }, null, 2));
  if (unsafeOrIncomplete) process.exitCode = 1;
}
main().catch(e => { console.error(e.stack || e); process.exitCode = 1; });
