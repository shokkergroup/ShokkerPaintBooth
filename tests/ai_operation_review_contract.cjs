'use strict';
// Frozen standalone lifecycle oracle, written before inspecting js/spb-ai-operation.js.
// These are manager invariants; no pro-AI dispatcher/native integration is implied.
const ORACLE = Object.freeze([
  { id: 'cancel-A-start-B-late-A', must: ['B remains current owner', 'A stale result and A finally cannot clear B', 'A cannot publish or restore over B'] },
  { id: 'repair-turn-new-collecting-generation', must: ['tool callback from prior turn is rejected after same-request repair starts', 'only current collecting generation can append/publish'] },
  { id: 'same-path-source-reload', must: ['path equality does not make stale generation current', 'source reload invalidates old operation'] },
  { id: 'element-reference-replacement', must: ['old target reference cannot write through newly replaced target', 'replacement is distinguished even at same path/index'] },
  { id: 'revision-conflict-protects-user-edit', must: ['preview snapshot restore is conditional on observed revision', 'later user edit is never clobbered'] },
  { id: 'publication-conflict-protects-newer-owner', must: ['stale publication cannot overwrite newer publication', 'failed publication remains visibly non-ready'] },
  { id: 'collecting-versus-ready', must: ['collecting descriptors are not advertised ready', 'ready requires explicit validated finish', 'terminal states reject late tool callbacks'] }
]);

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const Operation = require('../js/spb-ai-operation.js');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const sourcePath = path.join(root, 'js/spb-ai-operation.js');
const source = fs.readFileSync(sourcePath, 'utf8');
const SOURCE_SHA256 = '47587A1A53A35CE7E58825BAC864BD75C2421D26C19791957F57BB199A7000C6';
assert.equal(crypto.createHash('sha256').update(source).digest('hex').toUpperCase(), SOURCE_SHA256, 'test operates on frozen manager source');

const passed = [], failures = [], details = [];
function scenario(id, run) {
  try { const detail = run(); passed.push(id); details.push({ id, verdict: 'pass', ...detail }); }
  catch (e) { failures.push({ id, error: e.message }); details.push({ id, verdict: 'fail', reason: e.message }); }
}
function harness(readDoc, readRev) { return Operation.create(readDoc, readRev); }

scenario('cancel-A-start-B-late-A', () => {
  let doc = { sourcePath: 'car.psd', generation: 31, imageRef: {}, width: 2048 }, revision = 4;
  const m = harness(() => ({ ...doc }), () => revision), abortedA = { aborted: false, abort() { this.aborted = true; } };
  const a = m.start(abortedA), stale = m.bind({ queue: ['A'] }, a);
  assert.equal(m.cancel(a), true); assert.equal(abortedA.aborted, true);
  const b = m.start(), writes = [];
  assert.equal(m.current(b), true); assert.equal(m.owns(b), true);
  assert.equal(m.current(a), false); assert.equal(m.ticketOf(stale), a);
  assert.equal(m.publish(a, () => writes.push('A')).refused, true);
  assert.equal(m.restore(a, () => writes.push('restore-A')).refused, true);
  // A stale finally can query ownership but cannot cancel or clear B.
  assert.equal(m.cancel(a), false); assert.equal(m.owner(), b); assert.equal(m.current(b), true);
  assert.deepEqual(writes, []);
  return { owner: b.id, oldSignalAborted: abortedA.aborted, writes: writes.length };
});

scenario('repair-turn-new-collecting-generation', () => {
  const m = harness(() => ({ sourceGeneration: 8, sourcePath: 'car.psd' }), () => 0);
  const firstTurn = m.start(), oldToolResult = m.bind({ descriptor: 'old turn' }, firstTurn);
  const repairTurn = m.start(), newToolResult = m.bind({ descriptor: 'repair turn' }, repairTurn), accepted = [];
  function acceptToolResult(value) {
    const ticket = m.ticketOf(value);
    if (m.collecting(ticket)) accepted.push(value.descriptor);
  }
  acceptToolResult(oldToolResult); acceptToolResult(newToolResult);
  assert.equal(m.collecting(firstTurn), false);
  assert.equal(m.collecting(repairTurn), true);
  assert.deepEqual(accepted, ['repair turn']);
  assert.equal(m.ready(repairTurn), true);
  assert.equal(m.collecting(repairTurn), false);
  acceptToolResult(m.bind({ descriptor: 'late after ready' }, repairTurn));
  assert.deepEqual(accepted, ['repair turn']);
  return { oldTurnAccepted: false, readyTurnAccepted: true, lateAfterReadyAccepted: false };
});

scenario('same-path-source-reload-with-generation', () => {
  let doc = { path: 'car.psd', sourceGeneration: 4, sourceRef: 'session-4' };
  const m = harness(() => ({ ...doc }), () => 12), ticket = m.start();
  doc = { path: 'car.psd', sourceGeneration: 5, sourceRef: 'session-5' };
  let writes = 0;
  assert.equal(m.sameDocument(ticket), false);
  assert.equal(m.current(ticket), false);
  assert.equal(m.publish(ticket, () => { writes++; }).refused, true);
  assert.equal(writes, 0);
  return { samePath: true, oldGeneration: 4, currentGeneration: 5, writes };
});

scenario('same-path-source-reload-needs-controller-generation', () => {
  // Frozen oracle: without a generation, a same-path reload must not remain current.
  let doc = { path: 'car.psd' };
  const m = harness(() => ({ ...doc }), () => 1), ticket = m.start();
  doc = { path: 'car.psd' };
  assert.equal(m.current(ticket), false, 'same-path reload must be stale even if controller reports only path');
  return { pathOnlyIdentityCannotDistinguishReload: true };
});

// Post-review API boundary observation, separate from the frozen oracle: repaired manager
// intentionally refuses to activate path-only callers because no reload generation exists.
scenario('post-review-path-only-start-fails-closed', () => {
  const m = harness(() => ({ path: 'car.psd' }), () => 1), ticket = m.start();
  assert.equal(m.current(ticket), false);
  return { usableWithoutGeneration: false, failClosed: true };
});

// Adversarial supplement discovered during implementation inspection (not part of the
// pre-inspection oracle): verify whether create() snapshots a mutable descriptor itself.
scenario('readDocument-mutable-alias-is-not-snapshotted', () => {
  const doc = { sourcePath: 'car.psd', sourceGeneration: 1 };
  const m = harness(() => doc, () => 0), ticket = m.start();
  doc.sourceGeneration = 2;
  assert.equal(m.current(ticket), false, 'manager must detect mutation of its captured document identity');
  return { beforeGeneration: 1, afterGeneration: 2, staleDetected: !m.current(ticket) };
});

scenario('element-reference-replacement-same-path-and-slot', () => {
  let element = { token: 'object-1' }, doc = { sourceGeneration: 3, path: 'car.psd', elementRef: element, elementIndex: 2 };
  const m = harness(() => ({ ...doc }), () => 6), ticket = m.start(), writes = [];
  element = { token: 'object-2' }; doc = { ...doc, elementRef: element };
  assert.equal(m.current(ticket), false);
  assert.equal(m.publish(ticket, () => writes.push('old element')).refused, true);
  assert.deepEqual(writes, []);
  return { pathUnchanged: true, indexUnchanged: true, replacementDetected: true, writes: writes.length };
});

scenario('preview-restore-refuses-user-revision', () => {
  let revision = 20; const m = harness(() => ({ sourceGeneration: 1 }), () => revision), t = m.start();
  let writes = 0;
  assert.equal(m.publish(t, () => { writes++; revision++; }).refused, false);
  assert.equal(m.current(t), true, 'manager absorbs the revision caused by its own synchronous publication');
  revision++; // manual edit after the preview was published
  assert.equal(m.restore(t, () => { writes++; revision++; }).refused, true);
  assert.equal(writes, 1, 'manual revision must not be overwritten by restoration');
  return { previewPublished: true, manualRevisionPreserved: true, writeCount: writes };
});

scenario('stale-publication-refuses-new-owner', () => {
  const m = harness(() => ({ sourceGeneration: 7 }), () => 0), a = m.start(), writes = [];
  const b = m.start();
  const result = m.publish(a, () => writes.push('A'));
  assert.equal(result.refused, true); assert.equal(m.owner(), b); assert.equal(m.current(b), true);
  assert.equal(m.collecting(a), false); assert.deepEqual(writes, []);
  assert.equal(m.collecting(b), true);
  return { publicationRefused: result.refused, currentOwner: b.id, writes: writes.length };
});

scenario('collecting-ready-terminal-callback-gate', () => {
  const m = harness(() => ({ sourceGeneration: 9 }), () => 2), t = m.start(), readyDescriptor = m.bind({ queue: [] }, t), appended = [];
  assert.equal(m.collecting(t), true);
  assert.equal(m.ready(t), true); assert.equal(m.collecting(t), false);
  const late = m.bind({ queue: ['late'] }, t), addCallback = value => { if (m.collecting(m.ticketOf(value))) appended.push(value.queue[0]); };
  addCallback(late);
  assert.deepEqual(appended, []);
  assert.equal(m.current(t), true, 'ready is current but no longer collecting');
  assert.equal(m.ticketOf(readyDescriptor), t);
  return { phase: t.phase, currentAfterReady: m.current(t), collectingAfterReady: m.collecting(t), appendedLate: appended.length };
});

// Root-provided regression for same-request repair collection token. This does not count
// as pre-inspection holdout coverage; it checks the newly added exported manager API.
scenario('root-regression-same-ticket-collection-generation', () => {
  const m = harness(() => ({ sourceGeneration: 10 }), () => 3), t = m.start();
  const firstCollection = m.collect(t), secondCollection = m.collect(t);
  assert.ok(firstCollection < secondCollection);
  assert.equal(m.collecting(t, firstCollection), false, 'late prior-turn callback must be rejected');
  assert.equal(m.ready(t, firstCollection), false, 'old turn cannot mark the active turn ready');
  assert.equal(m.collecting(t, secondCollection), true);
  assert.equal(m.ready(t, secondCollection), true);
  return { firstCollection, secondCollection, oldTurnRejected: true, currentTurnReady: true };
});

console.log(`${failures.length ? 'FAIL' : 'PASS'} operation-manager review: ${passed.length}/${ORACLE.length + 4} scenarios`);
console.log(JSON.stringify(details, null, 2));
if (failures.length) { console.error(failures.map(f => `${f.id}: ${f.error}`).join('\n')); process.exitCode = 1; }
