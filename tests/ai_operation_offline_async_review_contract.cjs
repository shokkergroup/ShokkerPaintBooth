'use strict';
// W32 independent offline/async lifecycle oracle. These scenarios and invariants
// were fixed before reading the supplied candidate. Actual-source bindings follow.
const ORACLE = {
  frozenAt: '2026-10-04 before candidate inspection',
  candidateSha256: 'A656E3A2E55BD8E6D893BE47C12D3686CE30B682405DC33D170C354398DEE183',
  candidatePath: '_easy_claude_work/ai14h_w10_candidate/js/spb-pro-ai.js',
  cases: [
    { id: 'offline-refine-document-reload-during-preview', invariant: 'old preview/refine continuation cannot mutate or become a current answer after source generation changes' },
    { id: 'offline-part-lookup-replacement-during-await', invariant: 'late part lookup cannot publish ownership or answer against a replacement document' },
    { id: 'offline-spec-preview-manual-revision-conflict', invariant: 'manual edit during awaited settled preview is preserved and stale generated edit is rejected' },
    { id: 'offline-edit-delayed-answer-single-release', invariant: 'delayed offline edit holds busy until completion, then releases once without clearing a later owner' },
    { id: 'offline-look-preview-cancel-then-new-request', invariant: 'cancelled look/refine continuation cannot clear or write over a newer request' },
    { id: 'offline-ideas-picture-source-switch', invariant: 'late ideas/picture analysis is fenced from a different committed source' },
    { id: 'offline-material-plan-await-does-not-rebind', invariant: 'material preview begun for source A cannot re-target source B after await' },
    { id: 'ask-core-offline-selfhelp-delayed-completion', invariant: 'async offline helper result keeps request ownership and does not strand or clobber composer state' },
    { id: 'mark-elements-async-publication-source-change', invariant: 'late mark_elements publication requires same source/document and selection identity' },
    { id: 'refinish-and-add-graphic-late-callback-after-cancel-b', invariant: 'late refinish/add_graphic callbacks from A cannot publish into B after cancellation' }
  ]
};

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
// Parent moved the frozen bytes to an immutable pre-rebase snapshot after the
// originally named candidate path advanced. Keep the oracle's original target
// identity above and execute only the same verified SHA from this immutable copy.
const runtimeSnapshotPath = '_easy_claude_work/ai14h_w10_pre_rebase/js/spb-pro-ai.js';
const candidatePath = path.join(root, runtimeSnapshotPath);
const source = fs.readFileSync(candidatePath, 'utf8');
const sourceHash = crypto.createHash('sha256').update(source).digest('hex').toUpperCase();
assert.equal(sourceHash, ORACLE.candidateSha256, 'review candidate is the exact frozen W32 input');
const vm = require('node:vm');
function slice(start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a + start.length);
  assert(a >= 0 && b > a, `candidate boundary exists: ${start}`);
  return source.slice(a, b);
}
function deferred() { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
function world(parts = []) {
  const w = { console, Promise, Date, setTimeout: fn => { fn(); return 1; }, _busy: false, _progress: '', _absent: {}, _skipParts: true,
    _log: [], _offlineLast: null, zones: [], sourceGeneration: 1, layerRev: 0, undoCalls: [], rendered: 0, queue: [],
    _elemRunIdentity: null, _elemCache: null, _elemNone: {}, _taughtNow: {}, _elemOk: {}, _serial: 0,
    warm: () => Promise.resolve(), markPartFollowupQueue: () => {},
    friendlyZoneError: x => String(x), CAR: { missing: () => [] }, D: { nameColour: c => String(c), describePlan: () => 'test plan' },
    makeTools(q) { return [{ name: 'add_zone', handler: z => { q.push({ kind: 'add', spec: z }); return {}; } },
      { name: 'edit_zone', handler: z => { q.push({ kind: 'edit', spec: z }); return {}; } },
      { name: 'apply_scheme', handler: () => ({ ok: true }) }]; },
    _absent: {}, _taughtNow: {}, _elemOk: {}, operationOwner: 'A'
  };
  w.render = () => { w.rendered++; };
  w.doUndo = e => { w.undoCalls.push({ id: e.id, sourceGeneration: w.sourceGeneration }); };
  w.editReply = (text, chips, extra) => Object.assign({ offline: true, text, queue: [], usage: { cost: 0 }, calls: 0, model: 'built-in' }, extra || {});
  w.operationCanceled = () => ({ cancelled: true, stale: true, queue: [] });
  w.window = w; w.document = { getElementById: () => ({ width: 1024, height: 1024 }) };
  vm.createContext(w);
  vm.runInContext(slice('function offlineRefineAsk(text, rf, o)', 'function offlineCoveredPartAsk(text, proof, o)') +
    slice('function offlinePartAsk(text, pt, o)', 'function friendlyZoneError(msg)') +
    slice('function offlineSpecAsk(text, sp, o)', '// ------------------------------------------------------------------ EDIT WHAT IS ALREADY THERE') +
    slice('function markElements(kindIn, boxes, replace, extra)', '// WP12 2026-10-03 (owner law: on a FLAT paint') +
    slice('function operationTools(tools,queue,t,collection)', 'function operationFailure(ticket,error)'), w, { filename: 'actual-offline-async-slices.js' });
  return w;
}
async function runCases() {
  const rows = [];
  async function run(id, fn) { try { rows.push({ id, verdict: 'pass', ...(await fn()) }); } catch (e) { rows.push({ id, verdict: 'fail', reason: e.message }); } }
  await run('offline-refine-document-reload-during-preview', async () => {
    const w = world(), p = deferred(); w.warm = () => p.promise;
    const previous = { role: 'ai', id: 7, undoable: true, undone: false }; w._log = [previous]; w._offlineLast = { id: 7, plan: { elements: [], palette: {}, ctx: {} } };
    const run = w.offlineRefineAsk('make it softer', { plan: { elements: [], palette: {}, ctx: {} }, did: ['softer'] }, {});
    w.sourceGeneration++; p.resolve(); const result = await run;
    assert.equal(w.undoCalls.length, 0, 'stale source must not undo prior entry before returning a stale result');
    return { undoCalls: w.undoCalls, resultHasQueue: !!(result.queue && result.queue.length), sourceGeneration: w.sourceGeneration };
  });
  await run('offline-part-lookup-replacement-during-await', async () => {
    const w = world(), p = deferred(); w.warm = () => p.promise;
    const task = w.offlinePartAsk('paint roof', { parts: ['roof'], zones: [{ name: 'test roof', region: { part: 'roof' }, color: '#123456' }], colour: 'blue', finish: 'gloss' }, {});
    w._busy = true; w.operationOwner = 'B'; p.resolve(); await task;
    assert.equal(w._busy, true, 'completion owned by A must not clear B busy state');
    return { busyAfterA: w._busy, queueLength: w.queue.length, owner: w.operationOwner };
  });
  await run('offline-spec-preview-manual-revision-conflict', async () => {
    const w = world(), p = deferred(); w.warm = () => p.promise;
    const task = w.offlineSpecAsk('clearcoat roof', { parts: ['roof'], look: 'gloss', zones: [{ name: 'roof spec', region: { part: 'roof' }, color: '#123456' }] }, {});
    w.sourceGeneration++; w.layerRev++; p.resolve(); const result = await task;
    assert.equal(result.queue.length, 1, 'helper returns an unbound queue proposal after reload (not yet an applied write)');
    assert.equal(w.zones.length, 0, 'actual helper does not itself write the zone; the outer ask fence must discard this result');
    return { sourceGeneration: w.sourceGeneration, layerRev: w.layerRev, staleQueueReturned: true, directZoneMutations: 0, interpretation:'stale proposal only; ask wrapper must stop it from reaching finish/apply' };
  });
  await run('outer-ask-cancel-a-then-b-stale-result-fence', async () => {
    const w = world(), p = deferred(); let owner = null, serial = 0;
    w.operationStart = () => { owner = ++serial; return owner; };
    w.operationCurrent = t => t === owner;
    w.operationRelease = () => {};
    w.operationBind = (v, t) => Object.assign(v, { boundTicket: t });
    w.operationCanceled = () => ({ cancelled: true, stale: true, queue: [] });
    w.operationManager = () => ({ ready: () => {} });
    w.askForTicket = () => p.promise;
    vm.runInContext(slice('function ask(text,o)', 'function askForTicket(text, o)'), w, { filename: 'actual-ask-wrapper.js' });
    const a = w.ask('A', {}); owner = 999; p.resolve({ queue: [{ kind: 'edit' }], text: 'late A' });
    const got = await a;
    assert.equal(got.cancelled, true); assert.deepEqual(Array.from(got.queue), []);
    return { staleResultDiscarded: true, boundTicket: got.boundTicket };
  });
  await run('operation-tools-async-mark-callback-output-fence', async () => {
    const w = world(), p = deferred(); let collecting = true, mutated = false;
    w.operationManager = () => ({ collecting: () => collecting, publish: (t, f) => ({ value: f(), refused: false }) });
    w.operationPublish = (t, fn) => w.operationManager().publish(t, fn).value;
    const at = source.indexOf("name: 'mark_elements'");
    const hs = source.indexOf('handler: function (a) { return markElements(', at);
    assert(at >= 0 && hs > at, 'actual mark_elements tool handler located');
    const he = source.indexOf('} },', hs); assert(he > hs, 'actual mark_elements tool handler end located');
    w.E = { prepPalette: () => [{ name: 'white' }] };
    w.SpbProElements = { analyse: () => p.promise,
      modeFor: () => 'glyph', teachBoxes: () => { mutated = true; return { used: [[0,0,0.1,0.1]], colours: ['#ffffff'], share: 2, places: [], skipped: [], mode: 'glyph' }; },
      kinds: () => ({}), sig: () => 'changed-source-signature', remember: () => true };
    const handler = vm.runInContext('(' + source.slice(hs + 'handler: '.length, he + 1) + ')', w);
    const tools = w.operationTools([{ name: 'mark_elements', handler }], w.queue, 'ticket-A', 1);
    const resultPromise = tools[0].handler({ kind: 'numbers', boxes: [[0,0,0.1,0.1]] }); collecting = false; p.resolve({ changed: true });
    const result = await resultPromise;
    assert.equal(mutated, false, 'stale asynchronous callback must not publish a side effect');
    return { wrapperError: !!result.error, downstreamMutation: mutated };
  });
  return rows;
}
const reportPath = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_OPERATION_OFFLINE_ASYNC_REVIEW_2026-10-03.json');
(async () => {
  const out = await runCases();
  function lineAt(anchor, token) { const a=source.indexOf(anchor), p=a<0?-1:source.indexOf(token,a); return p<0?null:source.slice(0,p).split(/\r?\n/).length; }
  const staticFindings = [
    { caseId:'offline-edit-delayed-answer-single-release', sink:'offlineEditAsk awaits external look lookups with Promise.all and later prepEnv; these continuations do not capture/check the operation ticket.', lines:[lineAt('function offlineEditAsk(text, ed, o)','function offlineEditAsk'),lineAt('function offlineEditAsk(text, ed, o)','return Promise.all(jobs)'),lineAt('function offlineEditAsk(text, ed, o)','return (need.length ? warm(5000)')].filter(Boolean) },
    { caseId:'offline-look-preview-cancel-then-new-request', sink:'offlineLookAsk awaits warm and resolveLook; continuation builds a queue with makeTools(queue), outside operationTools.', lines:[lineAt('function offlineLookAsk(text, lr, o)','function offlineLookAsk'),lineAt('function offlineLookAsk(text, lr, o)','return warm(4000)'),lineAt('function offlineLookAsk(text, lr, o)','resolveLook(q, lr.colour)'),lineAt('function offlineLookAsk(text, lr, o)','var queue = [], tools = makeTools(queue)')].filter(Boolean) },
    { caseId:'offline-ideas-picture-source-switch', sink:'offlineIdeasAsk awaits warm and sequential async apply_scheme handlers; it clears shared _busy and constructs unbound queues via makeTools(queue).', lines:[lineAt('function offlineIdeasAsk(text, ideas, o)','function offlineIdeasAsk'),lineAt('function offlineIdeasAsk(text, ideas, o)','return warm(5000)'),lineAt('function offlineIdeasAsk(text, ideas, o)','_busy = false; var need'),lineAt('function offlineIdeasAsk(text, ideas, o)','chain0 = chain0.then'),lineAt('function offlineIdeasAsk(text, ideas, o)','var queue = [], tools = makeTools(queue)')].filter(Boolean) },
    { caseId:'offline-material-plan-await-does-not-rebind', sink:'offlineMaterialAsk awaits warm then reads live editEnv/zones and writes shared _busy=false; helper does not capture/check operation source identity.', lines:[lineAt('function offlineMaterialAsk(text, parsed)','function offlineMaterialAsk'),lineAt('function offlineMaterialAsk(text, parsed)','return warm(5000)'),lineAt('function offlineMaterialAsk(text, parsed)','_busy = false;'),lineAt('function offlineMaterialAsk(text, parsed)','editEnv()')].filter(Boolean) },
    { caseId:'mark-elements-async-publication-source-change', sink:'Actual markElements awaits El.analyse, then only checks elementRunIdentity (null on ordinary tool calls) before El.teachBoxes mutates ownership; the outer operationTools wrapper rejects the late return after the mutation has already occurred.', lines:[76,82,495,1346,1368,1370] },
    { caseId:'refinish-and-add-graphic-late-callback-after-cancel-b', sink:'operationTools validates at call entry and checks result after a promise, but cannot cancel delegated side effects already run inside that promise. refinish has an awaited pre/prepEnv path; add_graphic handler path was not dynamically exercised.', lines:[76,82,405,498] }
  ];
  const fails = out.filter(x => x.verdict === 'fail');
  const report = { status: fails.length ? 'FINDINGS' : 'PASS_WITH_LIMITS', task:'W32 independent offline/async tool lifecycle audit', candidate:{requestedPath:ORACLE.candidatePath,runtimeSnapshotPath,sha256:sourceHash,bytes:Buffer.byteLength(source),pathCorrection:'The requested candidate path advanced to a different hash before execution; parent supplied an immutable snapshot with the exact frozen hash. No runtime checks were run against the advanced path.'}, oracle:ORACLE,
    counts:{frozenCases:ORACLE.cases.length,runtimeCases:out.length,runtimeContractFailures:fails.length,runtimeConfirmedSinkReproductions:fails.filter(x=>x.id==='offline-refine-document-reload-during-preview'||x.id==='operation-tools-async-mark-callback-output-fence').length,runtimeConditionalOwnerHazards:fails.filter(x=>x.id==='offline-part-lookup-replacement-during-await').length,runtimePasses:out.length-fails.length,staleQueueProposals:out.filter(x=>x.staleQueueReturned).length,providers:0,nativeCalls:0},runtime:out,staticFindings,
    conclusions:['Offline ask wrapper has a final stale-ticket discard, which protects its returned result from reaching finish when ownership changed; the generic actual ask-wrapper scenario confirmed this containment.', 'The offlineSpecAsk probe returned a queued proposal after source-generation/revision change, but did not mutate zones. This is not a stale paint write; safe application relies on the outer ask ticket fence and the helper result is not independently source-bound.', 'Confirmed in the extracted helper body: offlineRefineAsk calls doUndo on the previous entry after an awaited warm without checking source generation. The controlled callback ran after sourceGeneration changed; in the real app this sink needs an owner/source guard because Undo mutates live state.', 'offlinePartAsk also clears shared _busy unconditionally after await. The reproduction manually modeled another busy owner already present; normal typed ask rejects a second ask while _busy is true, so this is a conditional ownership hazard rather than a demonstrated normal double-submit race.', 'operationTools provides call-entry and result-return fences, but it cannot reverse mutations performed inside a delegated async handler before its promise settles. mark_elements delegates to markElements without passing an operation token; reproduction uses only a controlled fake downstream mutation.'],
    limits:['Candidate is an exact parent-frozen temporary snapshot; live/shared production source was not read or edited.', 'Executed actual offlineRefineAsk, offlinePartAsk, offlineSpecAsk, ask wrapper, operationTools, markElements, and the exact mark_elements tool-handler source. Warm, CAR, and SpbProElements.teachBoxes are controlled callbacks. markElements itself reaches the async teachBoxes call after the stale boundary in the probe.', 'No real provider, browser, native app, renderer, MCP server, or external I/O was invoked. Refine/part helper effects do not prove a native paint write; queue publication is not the same as finish/apply.', 'The part busy-owner case injects B ownership before A resolves; ordinary typed ask blocks another ask while _busy remains true, so treat this as conditional takeover/alternate-owner evidence, not a demonstrated normal double-submit. Fresh oracle has ten cases, but only five runtime paths are directly exercised; five additional async paths are source-sink findings, not dynamic reproductions.'] };
  fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({status:report.status,counts:report.counts,failed: fails,report:reportPath},null,2));
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
