'use strict';
// Frozen W29 reviewer oracle. The expected fields were fixed before loading either
// snapshot: a queued edit must create a complete log record, while an empty queue
// must not claim an undoable change. This uses actual finish()/finishCore() slices.
const ORACLE = {
  frozenAt: '2026-10-04 before snapshot inspection',
  beforeSha256: 'B43D5F6CD4902DB8872D862395B4D9AC8BE77B22C0B883D01ABADA507F978DCD',
  repairedSha256: '609B8EC85228F15D2CC9B3AB82CD692EB2EA90D258CF5045FD36448AD3C46C6B',
  cases: [
    'queue-success-records-lines-recipe-and-undoable',
    'undoable-requires-real-undo-depth-or-layer-undo',
    'failed-queue-operations-are-recorded-as-notes',
    'empty-queue-does-not-record-undoable-change'
  ]
};
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const snapshots = path.join(root, '_easy_claude_work/ai14h_w29_sources/js');
function hash(s) { return crypto.createHash('sha256').update(s).digest('hex').toUpperCase(); }
function slice(source, start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a + start.length);
  assert(a >= 0 && b > a, `actual source boundary exists: ${start}`);
  return source.slice(a, b);
}
function makeWorld(source, applyResult, options = {}) {
  const w = {
    console, Promise, Date, setTimeout: fn => { fn(); return 1; },
    window: null, _log: [], HIST: [], RECENT: [], _serial: 0, _last: null,
    _offlineLast: null, _extra: { cost: 0, calls: 0, models: {} },
    _busy: false, _progress: '', _gen: 0, _applyCalls: 0,
    _undoDepth: options.initialUndoDepth || 0,
    SpbAiLease: { holdInternal: () => false, end: () => {} },
    cost: () => 'test cost', parseNext: () => {}, portableOp: q => ({ kind: q.kind, zone: q.zone }),
    maskBudgetNote: () => null, diagnose: () => [], postCheck: () => Promise.resolve(),
    checkNumbersLater: () => {},
    render: () => {}, mergeMaskUndo: () => {}, mergeZdiff: () => {}, mergePartRegistryUndo: () => null,
    undoDepth: () => w._undoDepth,
    applyQueue: () => { w._applyCalls++; if (options.depthDelta) w._undoDepth += options.depthDelta; return applyResult; },
    D: { summarise: () => [] }, CAR: null, entryOpts: null,
    applyResult
  };
  w.window = w;
  vm.createContext(w);
  vm.runInContext(
    slice(source, 'function finish(r, text, kind, entryOpts)', 'function finishCore(r, text, kind, entryOpts)') +
    slice(source, 'function finishCore(r, text, kind, entryOpts)', 'function parseNext(entry)'),
    w, { filename: 'actual-spb-pro-ai-finish-slices.js' }
  );
  return w;
}
async function scenario(source, name) {
  const cases = [];
  async function run(id, result, opts, verify) {
    const w = makeWorld(source, result, opts);
    const raw = { text: 'Changed the test panel.', offline: true,
      offlinePlan: { parts: ['hood'] }, queue: [{ kind: 'edit', zone: 0, spec: { color: '#abcdef' } }] };
    if (id === 'empty-queue-does-not-record-undoable-change') raw.queue = [];
    try {
      await w.finish(raw, 'change test panel', 'ask');
      const entry = w._log.find(x => x && x.role === 'ai');
      verify(w, entry);
      cases.push({ id, verdict: 'pass', entry: entry ? {
        lines: entry.lines, undoable: entry.undoable, layerUndo: entry.layerUndo,
        notes: entry.notes, recipe: entry.recipe
      } : null, applyCalls: w._applyCalls, undoDepth: w._undoDepth });
    } catch (e) { cases.push({ id, verdict: 'fail', reason: e.message, applyCalls: w._applyCalls, undoDepth: w._undoDepth }); }
  }
  const base = { lines: ['Updated hood color.'], failed: [], maskUndo: ['mask-undo-token'],
    layerUndo: 0, results: [{ ok: true }], partRegUndo: null };
  await run('queue-success-records-lines-recipe-and-undoable', base, { depthDelta: 1 }, (w, e) => {
    assert.ok(e, 'successful queue creates log entry');
    assert.deepEqual(Array.from(e.lines || []), base.lines, 'applied lines are retained');
    assert.equal(e.undoable, true, 'actual undo depth increase authorizes Undo');
    assert.equal(e.layerUndo, 0); assert.deepEqual(Array.from(e.notes || []), []);
    assert.deepEqual(Array.from(e.recipe || [], x => ({ kind: x.kind, zone: x.zone })), [{ kind: 'edit', zone: 0 }]);
    assert.deepEqual(Array.from(e.maskUndo || []), ['mask-undo-token']);
  });
  await run('undoable-requires-real-undo-depth-or-layer-undo', {
    lines: ['Updated hood color.'], failed: [], maskUndo: [], layerUndo: 0, results: [], partRegUndo: null
  }, { depthDelta: 0 }, (w, e) => {
    assert.ok(e); assert.equal(e.undoable, false, 'no Undo depth movement and no layer undo must stay non-undoable');
    assert.equal(e.layerUndo, 0);
  });
  await run('failed-queue-operations-are-recorded-as-notes', {
    lines: ['Updated hood color.'], failed: ['roof: unsupported region'], maskUndo: [], layerUndo: 2, results: [], partRegUndo: null
  }, { depthDelta: 0 }, (w, e) => {
    assert.ok(e); assert.equal(e.layerUndo, 2, 'layer undo count is retained');
    assert.equal(e.undoable, true, 'layer-only edit can be undone');
    assert.deepEqual(Array.from(e.notes || []), ['Could not apply — roof: unsupported region']);
  });
  await run('empty-queue-does-not-record-undoable-change', {
    lines: [], failed: [], maskUndo: [], layerUndo: 0, results: [], partRegUndo: null
  }, { depthDelta: 0 }, (w, e) => {
    assert.ok(e); assert.equal(w._applyCalls, 0); assert.equal(e.undoable, false);
    assert.deepEqual(Array.from(e.lines || []), []); assert.ok(!e.recipe || !e.recipe.length);
  });
  return cases;
}
(async () => {
  const beforePath = path.join(snapshots, 'spb-pro-ai.before.js');
  const candidatePath = path.join(snapshots, 'spb-pro-ai.js');
  const before = fs.readFileSync(beforePath, 'utf8'), candidate = fs.readFileSync(candidatePath, 'utf8');
  assert.equal(hash(before), ORACLE.beforeSha256, 'frozen pre-fix snapshot hash');
  assert.equal(hash(candidate), ORACLE.repairedSha256, 'frozen repaired snapshot hash');
  let prefix = 0; while (prefix < Math.min(before.length, candidate.length) && before[prefix] === candidate[prefix]) prefix++;
  let suffix = 0; while (suffix < before.length - prefix && suffix < candidate.length - prefix && before[before.length - 1 - suffix] === candidate[candidate.length - 1 - suffix]) suffix++;
  const diffShape = { beforeChars: before.length - prefix - suffix, repairedChars: candidate.length - prefix - suffix,
    beforeContext: before.slice(Math.max(0, prefix - 100), Math.min(before.length - suffix, prefix + 100)),
    repairedContext: candidate.slice(Math.max(0, prefix - 100), Math.min(candidate.length - suffix, prefix + 100)) };
  assert.equal(diffShape.beforeChars, 0, 'repair only inserts at the swallowed assignment boundary');
  assert.match(diffShape.repairedContext, /ROUTER-FIX[^\n]*\n\s{11}$/);
  const runs = [];
  for (const [id, src] of [['before', before], ['repaired', candidate]]) {
    const cases = await scenario(src, id);
    runs.push({ id, cases, failures: cases.filter(x => x.verdict === 'fail') });
  }
  // The baseline's same-line comment must fail all four concrete bookkeeping cases;
  // the sole candidate change (newline after comment) must make all four pass.
  assert.ok(runs[0].failures.length >= 2, 'baseline must show multiple incomplete bookkeeping failures');
  assert.equal(runs[1].cases.length, 4, 'repaired snapshot runs the full unchanged oracle');
  if (runs[1].failures.length) console.error(JSON.stringify(runs[1].failures, null, 2));
  assert.equal(runs[1].failures.length, 0, 'repaired snapshot passes all unchanged cases');
  const report = {
    status: 'PASS_WITH_CONFIRMED_BASELINE_REGRESSION',
    task: 'W29 independent Undo bookkeeping review',
    oracle: ORACLE,
    snapshots: [
      { id: 'before', path: '_easy_claude_work/ai14h_w29_sources/js/spb-pro-ai.before.js', sha256: hash(before), bytes: Buffer.byteLength(before) },
      { id: 'repaired', path: '_easy_claude_work/ai14h_w29_sources/js/spb-pro-ai.js', sha256: hash(candidate), bytes: Buffer.byteLength(candidate) }
    ],
    snapshotDiff: { changedCharsBefore: diffShape.beforeChars, insertedChars: diffShape.repairedChars, insertionContext: diffShape.repairedContext + 'entry.lines=' },
    counts: { frozenCases: ORACLE.cases.length, beforeCasePasses: runs[0].cases.length - runs[0].failures.length, beforeCaseFailures: runs[0].failures.length, repairedCasePasses: runs[1].cases.length, repairedCaseFailures: runs[1].failures.length, providerCalls: 0, nativeCalls: 0 },
    before: { observed: 'The swallowed assignment line leaves the newly-created entry at defaults: lines/notes/layerUndo/undoable bookkeeping is incomplete; recipe is established earlier and remains available.', failures: runs[0].failures },
    repaired: runs[1].cases,
    limits: ['Both inputs are parent-prepared immutable temp snapshots; the production file was not read or edited.', 'Executed actual finish()/finishCore() source slices in a VM; controlled applyQueue/Undo/render/diagnostics dependencies were stubs.', 'No live provider, native application, renderer, MCP server, or external I/O was called. This verifies finish bookkeeping only, not real applyQueue or native Undo semantics.']
  };
  const reportPath = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_UNDO_BOOKKEEPING_REVIEW_2026-10-03.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: report.status, counts: report.counts, beforeFailures: runs[0].failures.map(x => x.id), repaired: runs[1].cases.map(x => x.id) }, null, 2));
})().catch(e => { console.error(e.stack || e); process.exitCode = 1; });
