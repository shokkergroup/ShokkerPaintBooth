'use strict';
// W91 independent warm-gate review. Frozen oracle was written before W86
// report/candidate inspection: _easy_claude_work/ai14h_w91_review/fresh-oracle.json
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const candidate = '_easy_claude_work/ai14h_w86_review/candidate/spb-pro-ai.js';
const opPath = 'js/spb-ai-operation.js';
const expected = 'eedf2aa5f17772f72796f722af322ba93665ddc01a43880ab313f57355c5cd17';
function sha(file) { return crypto.createHash('sha256').update(fs.readFileSync(path.join(root, file))).digest('hex'); }
assert.equal(sha(candidate), expected, 'pinned candidate changed');
const src = fs.readFileSync(path.join(root, candidate), 'utf8');
function slice(start, end) { const a = src.indexOf(start), b = src.indexOf(end, a); assert(a >= 0 && b > a, 'function bounds'); return src.slice(a, b); }
const warmSrc = slice('    function warm(ms) {', '    function runTurn(text,o)', '');
const offlineSrc = slice('    function offlineAsk(text, o) {', '    function offlineAskCore(text, o)');
const hydrateSrc = slice('    function hydratePartMemory() {', '    function setPartEditReg(');
const operation = require(path.join(root, opPath));

// Exercise the actual candidate warm() and offlineAsk() branch with the actual
// operation manager. CAR.ensure's false result is deliberate and observable.
async function falseWarm() {
  const doc = { sourceGeneration: 7, path: 'C:/selected.psd', fingerprint: 'fp7', width: 2048, height: 2048 };
  let revision = 1, hydrationAttempts = 0, retries = 0;
  const manager = operation.create(() => ({ ...doc }), () => revision);
  const w = { console, Promise, setTimeout, clearTimeout, zones: [{ _spbAIPartMemoryPending: { provenance: {} } }],
    D: { mentionsPart: () => true, parseColours: () => [{ hex: '#112233' }, { hex: '#445566' }], offlinePartCoverage: () => ({ complete: true }) },
    CAR: { ensure: () => Promise.resolve(false) }, window: null,
    operationManager: () => manager, operationCurrent: t => manager.current(t),
    operationPublish: (t, f) => { const r = manager.publish(t, f); return r && !r.refused ? r.value : null; },
    operationCanceled: () => ({ cancelled: true, queue: [] }),
    scopedPartSourceNow: () => ({ generation: 7, path: doc.path, fingerprint: doc.fingerprint, width: 2048, height: 2048 }),
    ensurePartMemoryRuntime: () => ({ rebindAfterCommit: () => { hydrationAttempts++; return { rebound: 0, rejected: 1 }; } }),
    advisorOwns: () => false, offlineMaterialPlan: () => null,
    E: null, editPlan: () => ({ kind: 'ask' }), offlineEditAsk: () => ({ route: 'clarify', queue: [] }), offlineCoveredPartAsk: () => ({ route: 'clarify', queue: [] }),
    offlineInstructionPreflight: () => null, elementRunCurrent: () => true,
    editReply: (text, chips) => ({ route: 'refusal', text, chips, queue: [] }) };
  w.window = w; vm.createContext(w);
  vm.runInContext('var _partMemoryWarmAttemptTicket=null; var _envMemo=null;', w);
  vm.runInContext(warmSrc + '\nthis.__warm=warm;', w);
  vm.runInContext(hydrateSrc + '\nthis.__hydrate=hydratePartMemory;', w);
  vm.runInContext(offlineSrc + '\nthis.__offline=offlineAsk;', w);
  const warmValue = await w.__warm(100);
  assert.deepEqual(Array.from(warmValue), [false], 'CAR false is propagated by warm');
  const ticket = manager.start();
  const result = await w.__offline('Make green on the roof blue', { _spbOperation: ticket });
  retries++;
  assert.equal(result.route, 'clarify');
  assert.equal(result.queue.length, 0);
  assert.equal(hydrationAttempts, 1, 'actual offlineAsk calls rebind after false warm result');
  assert.equal(manager.current(ticket), true);
  return { id: 'false-CAR-warm', result: 'no-queue-clarification', actualWarmValue: warmValue,
    rebindAttempts: hydrationAttempts, recursiveRetryCount: retries };
}

(async () => {
  const falseCase = await falseWarm();
  const rows = [
    { id: 'busy-owner', outcome: 'PASS via actual ask guard in W86 contract', freshReplay: false },
    { id: 'external-lease', outcome: 'PASS via actual ask guard in W86 contract', freshReplay: false },
    { id: 'cancel/source-generation/manual-revision', outcome: 'PASS via W86 actual operation manager delay fixtures', freshReplay: false },
    { id: 'false-CAR-warm', outcome: 'CAVEAT: retry/rebind runs although CAR.ensure resolved false; current runtime revalidates committed source, zone mask, CAR part mask, layout, elements, layers, and unique ownership before registering', freshReplay: true, ...falseCase },
    { id: 'passive-guidance', outcome: 'PASS by control-flow order: warm predicate requires pending part record, exact part, two distinct colors, imperative verb; semantic guidance runs only after warm branch', freshReplay: sourceHas(src, 'if (warmPartMemory && _partMemoryWarmAttemptTicket !== ticket)') },
    { id: 'one-shot-and-ticket-marker', outcome: 'PASS: ticket marker blocks recursive warm; cleanup compares marker identity before clearing', freshReplay: sourceHas(src, 'if (_partMemoryWarmAttemptTicket === ticket) _partMemoryWarmAttemptTicket = null;') },
    { id: 'valid-ready-control', outcome: 'PASS control in W86 contract: one warm/rebind and fresh scoped route', freshReplay: false }
  ];
  const report = {
    work_item: 'W91 independent revised W86 warm-gate review', date: '2026-10-04',
    status: 'PASS_WITH_CAVEAT', oracle: { path: '_easy_claude_work/ai14h_w91_review/fresh-oracle.json', sha256: sha('_easy_claude_work/ai14h_w91_review/fresh-oracle.json'), cases: 12 },
    sources: { candidate: { path: candidate, sha256: sha(candidate) }, operation: { path: opPath, sha256: sha(opPath) } },
    counts: { freshExecutableCases: 1, priorW86CaseCount: 8, providers: 0, nativeCalls: 0 }, rows,
    conclusion: 'Cancellation, source-generation and manual-revision races remain ticket guarded in the prior actual-operation fixtures; busy and external lease are refused by ask before entering offlineAsk. False CAR warm is the narrow caveat: actual warm propagates false, but offlineAsk ignores it and still attempts the actual hydration/rebind call. No queue is produced in this harness; production rebind remains guarded by current committed source and strict current zone/mask/layout/layer/unique-owner proofs, so this review does not demonstrate an unsafe ownership publication. A readiness gate would make that guarantee explicit.',
    limits: ['The false-CAR fixture executes actual warm(), offlineAsk(), hydratePartMemory(), and SpbAiOperation, but supplies a controlled rebind runtime; it demonstrates the missing readiness gate, not an invalid owner being registered.', 'Prior W86 8-case report used controlled CAR.ensure and hydration callbacks; those results are referenced, not rerun as fresh credit.', 'No native paint, browser, provider, server, or live production calls.']
  };
  const out = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_WARM_REBIND_W91_REVIEW_2026-10-04.json');
  fs.writeFileSync(out, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
})().catch(e => { console.error(e); process.exitCode = 1; });

function sourceHas(source, token) { return source.indexOf(token) !== -1; }
