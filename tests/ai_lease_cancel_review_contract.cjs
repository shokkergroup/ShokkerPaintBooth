'use strict';
// Lifecycle oracle fixed before reading lease/helper implementation.
// Fake promises only. Every accepted write must belong to the current request,
// current lease owner, current document and intended element identity.
const ORACLE = {
  leaseSourceSha256: 'D765444136C8CAE6FD46C79BC0730D5B9266AD70EA832BFB08438AB77CA0AD75',
  proAiSourceSha256: '115F602D49E465B6F49530B07A4C2E4B81E8D6089C2D8204BCAE9D57807690D4',
  scenarios: [
    { id: 'delayed-provider-and-finish', invariants: ['composer remains recoverable while pending', 'successful current reply applies once'] },
    { id: 'stop-then-new-request', invariants: ['Stop aborts old request', 'old reply cannot write or clear new busy state'] },
    { id: 'provider-ignores-stop-signal', invariants: ['late response after Stop cannot apply'] },
    { id: 'provider-rejection', invariants: ['request settles with recoverable error', 'busy and controller release'] },
    { id: 'synchronous-provider-throw', invariants: ['synchronous failure settles safely', 'composer and busy state recover'] },
    { id: 'document-switch', invariants: ['old-document answer cannot apply to current document'] },
    { id: 'element-identity-change', invariants: ['replacement target is rejected before apply'] },
    { id: 'external-active-expiry', invariants: ['active external owner remains exclusive past idle TTL', 'settlement releases busy'] },
    { id: 'external-rejection-and-missing-render', invariants: ['failure is explicit', 'lease and busy recover'] },
    { id: 'cancel-delayed-preview', invariants: ['snapshot restores', 'subsequent options stop', 'busy clears'] }
  ]
};

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const leaseSource = fs.readFileSync(path.join(root, 'js/spb-ai-lease.js'), 'utf8');
const proSource = fs.readFileSync(path.join(root, 'js/spb-pro-ai.js'), 'utf8');
const crypto = require('node:crypto');
assert.equal(crypto.createHash('sha256').update(leaseSource).digest('hex').toUpperCase(), ORACLE.leaseSourceSha256, 'lease source is the frozen review input');
assert.equal(crypto.createHash('sha256').update(proSource).digest('hex').toUpperCase(), ORACLE.proAiSourceSha256, 'pro-AI source is the frozen review input');
function slice(source, start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a + start.length);
  assert(a >= 0 && b > a, `actual-source boundaries exist: ${start}`);
  return source.slice(a, b);
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}
function makeWorld() {
  const w = {
    console, Promise, AbortController, setTimeout: fn => { fn(); return 1; }, Date,
    document: {}, _busy: false, _ctl: null, _cancelOpts: false,
    _progress: '', _extra: { cost: 0, calls: 0 }, _log: [], _serial: 0,
    _offlineLast: null, _last: null, _orig: null, _skipParts: true,
    HIST: [], RECENT: [], selectedZoneIndex: -1, zones: [], writes: [],
    docId: 'doc-A', renderCalls: 0, providerMode: null
  };
  w.window = w;
  vm.createContext(w);
  vm.runInContext(leaseSource, w, { filename: 'js/spb-ai-lease.js' });

  w.warm = () => Promise.resolve();
  w.intentSpecOnly = () => false;
  w.makeTools = () => [];
  w.elementRunCurrent = identity => !!identity && identity === w.currentIdentity;
  w.elementPaintChangedResult = () => ({ elementPaintChanged: true, queue: [], text: 'paint changed' });
  w.elementRunResult = (p, identity, read) => Promise.resolve(p).then(r => identity && read() !== identity ? w.elementPaintChangedResult() : r,
    e => identity && read() !== identity ? w.elementPaintChangedResult() : { error: { message: String(e && e.message || e) }, queue: [] });
  w.K = null; w.HOWTO_RE = /$a/; w.REVIEW = undefined;
  w.Z = { whenSettled: () => Promise.resolve(), previewImage: () => null, footprint: () => null };
  w.D = { recipes: () => [], summarise: () => [] };
  w.isSchemeRequest = () => false; w.state = () => ({ docId: w.docId });
  w.buildSystem = () => 'test'; w.onEvent = () => {}; w.CAR = null;
  w.AI = { cached: () => ({ configured: true }), run: opts => w.providerMode(opts) };
  w.offlineFirst = () => false; w.offlineCanHandle = () => false;
  w.selfHelpClaim = () => null; w.selfHelpResult = r => r; w.editPlan = () => null; w.offlineMaterialPlan = () => null;
  w.panelsNeeded = () => []; w.askCore = (text, o) => w.runTurn(text, o);

  w._applyCount = 0;
  w.applyQueue = queue => {
    w._applyCount++;
    w.writes.push({ docId: w.docId, queue: JSON.parse(JSON.stringify(queue)) });
    return { lines: ['updated zone'], failed: [], maskUndo: [], layerUndo: 0, results: [], partRegUndo: null };
  };
  w.undoDepth = () => w._applyCount;
  w.portableOp = () => null; w.maskBudgetNote = () => null; w.diagnose = () => [];
  w.cost = () => 'test'; w.parseNext = () => {}; w.postCheck = () => Promise.resolve();
  w.render = () => { w.renderCalls++; };
  w.friendlyError = e => String(e && e.message || e);
  w.elementRunCanceled = () => { w._busy = false; w._progress = ''; w._ctl = null; w.cancelled++; return { cancelled: true }; };
  w.cancelled = 0;
  w.captureOriginal = () => {};
  w.snapshotZones = () => [{ name: 'body' }]; w.restoreZones = () => { w.restoreCount++; return true; }; w.restoreCount = 0;
  w.Z.whenSettled = () => Promise.resolve();
  w._panel = { querySelector: () => w.input };
  w.input = { value: '' };
  w.elemCurrentCard = () => null; w.elementPaintSig = () => ''; w.elementRunIdentity = () => '';
  w.elemReplyAction = () => null; w.runElemAction = () => false; w.elemOwnsText = () => false;
  w.advisorIntent = () => null; w.TEACH_RE = /$a/; w.QUESTION_RE = /\?/; w.START_OVER_RE = /$a/;
  w.CHECK_AGAIN_RE = /$a/; w.NUM_FIX_RE = /$a/; w.CLAIM_RE = /\bApplied\b/;
  w.supportClass = () => null; w.supportSend = () => false; w.offlineCannot = () => false;
  w.layerVisRequest = () => false; w.offlineHowtoPeek = () => false; w.offlineScopeReply = () => ({ text: 'scope' });

  vm.runInContext(slice(proSource, 'function runTurn(text, o)', 'function runTurn2(text, o)') +
    slice(proSource, 'function runTurn2(text, o)', 'function askCore(text, o)') +
    slice(proSource, 'function finish(r, text, kind, entryOpts)', 'function finishCore(r, text, kind, entryOpts)') +
    slice(proSource, 'function finishCore(r, text, kind, entryOpts)', 'function parseNext(entry)') +
    slice(proSource, 'function mcpCall(tool, args)', 'function mcpCallCore(tool, args)') +
    slice(proSource, 'function ask(text, o)', '// ---- what colours') +
    slice(proSource, 'function previewOptions(entry, r, text)', 'function useOption(entry, i)'), w, { filename: 'actual-pro-ai-slices.js' });
  const cancelStart = proSource.indexOf("if (b.hasAttribute('data-cancel')) {");
  const cancelEnd = proSource.indexOf("var act = b.getAttribute('data-act')", cancelStart);
  assert(cancelStart >= 0 && cancelEnd > cancelStart, 'actual Stop/Cancel handler found');
  vm.runInContext('function clickCancel(b) {' + proSource.slice(cancelStart, cancelEnd) + '}', w, { filename: 'actual-cancel-branch.js' });
  return w;
}

const failures = [], passed = [], details = [];
function check(name, fn) { try { fn(); passed.push(name); } catch (e) { failures.push(`${name}: ${e.message}`); } }
async function scenario(name, fn) { try { const out = await fn(); passed.push(name); details.push({ id: name, verdict: 'pass', ...out }); } catch (e) { failures.push(`${name}: ${e.message}`); details.push({ id: name, verdict: 'fail', reason: e.message }); } }
const flush = async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); };

(async () => {
  await scenario('delayed provider and duplicate-writer guard', async () => {
    const w = makeWorld(), p = deferred(); w.SpbAiLease.internal(); w.providerMode = () => p.promise;
    const run = w.ask('change roof', {}); await flush();
    assert.equal(w._busy, true); assert.ok(w._ctl && !w._ctl.signal.aborted);
    p.resolve({ text: 'Changed roof.', queue: [{ kind: 'edit', zone: 0 }], tools: ['edit_zone'], calls: 1 });
    const r = await run;
    // Provider stubs do not invoke the real tool callbacks; emulate their collected queue.
    r.queue = [{ kind: 'edit', zone: 0 }];
    await w.finish(r, 'change roof', 'ask');
    assert.equal(w._applyCount, 1); assert.equal(w._busy, false);
    return { applyCount: w._applyCount, busyAfter: w._busy };
  });

  await scenario('Stop aborts real runTurn signal and permits a fresh request', async () => {
    const w = makeWorld(), pending = deferred(); w.SpbAiLease.internal();
    w.providerMode = opts => new Promise((resolve, reject) => {
      const abort = () => { const e = new Error('aborted'); e.name = 'AbortError'; reject(e); };
      opts.signal.addEventListener('abort', abort, { once: true });
      pending.promise.then(resolve, reject);
    });
    const old = w.ask('old request', {}); await flush();
    const oldSignal = w._ctl.signal;
    w.clickCancel({ hasAttribute: n => n === 'data-cancel' });
    assert.equal(oldSignal.aborted, true); assert.equal(w._cancelOpts, true);
    const oldResult = await old;
    await w.finish(oldResult, 'old request', 'ask');
    assert.equal(w._busy, false); assert.equal(w._applyCount, 0);
    const nextDeferred = deferred(); w.providerMode = () => nextDeferred.promise;
    const next = w.ask('new request', {}); await flush();
    assert.equal(w._busy, true); assert.equal(w._applyCount, 0);
    nextDeferred.resolve({ text: 'No changes.', queue: [], tools: [], calls: 1 });
    await next;
    return { oldError: oldResult.error && oldResult.error.message, newRequestStarted: true, writes: w._applyCount };
  });

  await scenario('late provider response after Stop is discarded', async () => {
    const w = makeWorld(), pending = deferred(); w.SpbAiLease.internal();
    w.providerMode = () => pending.promise; // deliberately ignores AbortSignal
    const old = w.ask('old request', {}); await flush();
    w.clickCancel({ hasAttribute: n => n === 'data-cancel' });
    assert.equal(w._ctl.signal.aborted, true);
    pending.resolve({ text: 'Late success.', tools: ['edit_zone'], calls: 1 });
    const result = await old; result.queue = [{ kind: 'edit', zone: 0 }];
    await w.finish(result, 'old request', 'ask');
    assert.equal(w._applyCount, 0, 'a request canceled by the user must not apply if provider ignores abort');
    return { cancelledFlag: w._cancelOpts, lateReplyError: result.error || null, writes: w._applyCount };
  });

  await scenario('provider rejection releases the current turn', async () => {
    const w = makeWorld(); w.SpbAiLease.internal();
    w.providerMode = () => Promise.reject(new Error('fake provider failure'));
    const result = await w.ask('request', {});
    assert.match(result.error.message, /fake provider failure/);
    assert.equal(w._busy, false); assert.equal(w._ctl, null); assert.equal(w._applyCount, 0);
    return { error: result.error.message, busyAfter: w._busy, writes: w._applyCount };
  });

  await scenario('synchronous provider throw releases the current turn', async () => {
    const w = makeWorld(); w.SpbAiLease.internal();
    w.providerMode = () => { throw new Error('fake synchronous throw'); };
    let error; try { await w.ask('request', {}); } catch (e) { error = e; }
    assert.ok(error, 'the fake synchronous throw rejects');
    assert.equal(w._busy, false, 'busy must clear after synchronous provider throw');
    assert.equal(w._ctl, null); assert.equal(w._applyCount, 0);
    return { caught: String(error), busyAfter: w._busy };
  });

  await scenario('ordinary document switch is checked before applying a delayed answer', async () => {
    const w = makeWorld(), p = deferred(); w.SpbAiLease.internal(); w.providerMode = () => p.promise;
    const run = w.ask('paint current roof red', {}); await flush();
    w.docId = 'doc-B';
    p.resolve({ text: 'Changed roof.', queue: [{ kind: 'edit', zone: 0 }], tools: ['edit_zone'], calls: 1 });
    const r = await run; r.queue = [{ kind: 'edit', zone: 0 }]; await w.finish(r, 'paint current roof red', 'ask');
    assert.equal(w._applyCount, 0, 'old-document answer must not write to current document');
    return { writes: w._applyCount, expectedDoc: 'doc-A', currentDoc: w.docId };
  });

  await scenario('element-scoped document identity rejects delayed reply', async () => {
    const w = makeWorld(), p = deferred(); w.SpbAiLease.internal();
    w.currentIdentity = 'element-A'; w.providerMode = () => p.promise;
    const run = w.ask('paint this learned element', { elementRunIdentity: 'element-A' }); await flush();
    w.currentIdentity = 'element-B';
    p.resolve({ text: 'Changed element.', queue: [{ kind: 'edit', zone: 0 }], tools: ['edit_zone'], calls: 1 });
    const r = await run; await w.finish(r, 'paint this learned element', 'ask', { elementRunIdentity: 'element-A' });
    assert.equal(r.elementPaintChanged, true); assert.equal(w._applyCount, 0); assert.equal(w.cancelled, 1);
    return { cancelled: r.elementPaintChanged, writes: w._applyCount };
  });

  await scenario('external takeover remains busy through expiry and releases on settlement', async () => {
    const w = makeWorld(), p = deferred(); let now = 1000; w.Date = { now: () => now };
    w.SpbAiLease.release();
    w.mcpCallCore = () => p.promise;
    const call = w.mcpCall('edit_zone', {}); await flush();
    assert.equal(w.SpbAiLease.owner(), 'external'); assert.equal(w._busy, true);
    now += 120001;
    assert.equal(w.SpbAiLease.owner(), 'external', 'active lease does not expire while writer is pending');
    assert.equal(w.SpbAiLease.begin('internal'), false, 'no second owner enters while external call is active');
    const refused = await w.ask('new internal ask', {});
    assert.match(refused.error.message, /external AI/);
    p.resolve({ ok: true }); const result = await call;
    assert.equal(result.ok, true); assert.equal(w._busy, false);
    assert.equal(w.SpbAiLease.takeover(), true, 'idle external owner can be taken over after completion');
    return { ownerDuringExpiry: 'external', busyAfterSettlement: w._busy, takeoverAfter: true };
  });

  await scenario('external core rejection and missing render do not strand lease/composer', async () => {
    const w = makeWorld(); w.SpbAiLease.release();
    w.mcpCallCore = () => Promise.reject(new Error('fake MCP failure'));
    w.render = undefined;
    const result = await w.mcpCall('edit_zone', {});
    assert.equal(result.ok, false); assert.match(result.error, /fake MCP failure/);
    assert.equal(w._busy, false); assert.equal(w.SpbAiLease.owner(), 'external');
    return { result: result.error, busyAfter: w._busy, renderMissing: true };
  });

  await scenario('cancel during delayed option preview restores paint and frees composer', async () => {
    const w = makeWorld(), gate = deferred(); let settles = 0;
    w.SpbAiLease.internal(); w._cancelOpts = false;
    w.Z.whenSettled = () => (++settles === 1 ? gate.promise : Promise.resolve());
    const entry = { role: 'ai', id: 1, text: '', lines: [], notes: [] };
    const run = w.previewOptions(entry, { text: '', queue: { options: [
      { label: 'A', queue: [{ kind: 'edit', zone: 0 }] }, { label: 'B', queue: [{ kind: 'edit', zone: 1 }] }
    ] } }, 'choose a look');
    await flush(); assert.equal(w._applyCount, 1); assert.equal(w._busy, true);
    w.clickCancel({ hasAttribute: n => n === 'data-cancel' });
    gate.resolve(); await run;
    assert.equal(w._busy, false); assert.equal(w.restoreCount, 2, 'preview snapshot is restored before idle');
    assert.equal(w._applyCount, 1, 'second option is not previewed after Cancel');
    return { restores: w.restoreCount, attemptedPreviews: w._applyCount, retainedOptions: entry.options.length, busyAfter: w._busy };
  });

  console.log(`${failures.length ? 'FAIL' : 'PASS'} lease/cancel review: ${passed.length}/${ORACLE.scenarios.length} scenarios`);
  console.log(JSON.stringify(details, null, 2));
  if (failures.length) { console.error(failures.join('\n')); process.exitCode = 1; }
})().catch(e => { console.error(e); process.exitCode = 1; });
