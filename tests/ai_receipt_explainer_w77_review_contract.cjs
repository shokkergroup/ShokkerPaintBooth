'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const crypto = require('node:crypto');

const controllerPath = '_easy_claude_work/ai14h_generation3_candidate/integration9/js/spb-pro-ai.js';
const explainerPath = '_easy_claude_work/ai14h_generation3_candidate/integration9/js/spb-ai-receipt-explainer.js';
const oraclePath = '_easy_claude_work/ai14h_w77_review_fresh_oracle.json';
const pins = new Map([
  [controllerPath, 'aae99cdd02b00bdd78d1f02fed85c18bc72b82cab9a66ceb7e0e3590ec3e8790'],
  [explainerPath, '25aba5ee85e9c9fb7efe3603fce22b140ccb09d2cbd09a9303ac6ab00530eac3'],
  [oraclePath, '2eae9c329200f6923a5fbd22ede792498c218596d5af1c569098f22d473a5888']
]);
for (const [file, wanted] of pins) {
  const got = crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  assert.equal(got, wanted, `pinned W77 input changed: ${file}`);
}

// Reuse the existing actual-route harness in memory, extending it with fresh
// assertions. The original contract/oracle remains untouched on disk.
const harnessPath = 'tests/ai_receipt_explainer_w77_contract.cjs';
const original = fs.readFileSync(harnessPath, 'utf8');
const marker = "  console.log('PASS W77 offline receipt route:";
assert(original.includes(marker), 'existing W77 actual-route test insertion point exists');
const fresh = `
  // R01/R02: apply publication is a revision-changing synchronous mutation;
  // operationPublish must refresh the owning ticket before finishCore binds
  // the receipt. A current receipt must still explain the applied line.
  reset();
  var priorApplyQueue = w.applyQueue;
  w.applyQueue = function () { var a = priorApplyQueue.apply(this, arguments); if (a && a.lines && a.lines.length) w._spbLayerRev++; return a; };
  await w.makeAppliedReceipt('Roof: finish base::f_clear_satin');
  var successEntry = w._log[w._log.length - 1], successTicket = successEntry._spbOperation;
  assert.ok(successTicket, 'finishCore binds the receipt to its publishing ticket');
  assert.equal(successTicket.revision, vm.runInContext('operationRevision()', w), 'finishCore receipt ticket captures post-publish revision');
  assert.equal(w.currentReceipt(successEntry), true, 'published receipt remains current after the apply changed revision');
  var successReply = await route('Explain my last change');
  assert.match(successReply.r.text, /Roof: finish base::f_clear_satin/);

  // R03: a later failed-only attempt is the latest receipt candidate, so the
  // previous successful line must not be presented as the last attempt.
  w.applyResult = {lines:[],failed:['hood selector unavailable'],maskUndo:[],layerUndo:0,undoSnap:null,zPushed:[],lPushed:[],results:[]};
  await w.makeAppliedReceipt('Failed hood attempt');
  var failedEntry = w._log[w._log.length - 1];
  assert.equal(failedEntry.lines.length, 0);
  assert.ok(failedEntry.notes.some(function (n) { return /hood selector unavailable/.test(n); }));
  var failedReply = await route('Explain the last attempt');
  assert.match(failedReply.r.text, /last recorded attempt did not apply/i);
  assert.match(failedReply.r.text, /hood selector unavailable/);
  assert.doesNotMatch(failedReply.r.text, /Roof: finish base::f_clear_satin/);

  // R08/R09: mixed action-and-explanation wording cannot be consumed as a
  // read-only receipt request; the actual action route retains the full text.
  reset();
  var queueBeforeMixed = w.queueMutations;
  w.routeSend('Change the roof to blue and explain my last change');
  await Promise.resolve();
  assert.deepEqual(w.sentAsk, ['Change the roof to blue and explain my last change']);
  assert.equal(w.queueMutations, queueBeforeMixed);
  assert.equal(w.providerCalls, 0);
  w.applyQueue = priorApplyQueue;
`;
const extended = original.replace(marker, fresh + '\n' + marker);
const temporaryHarness = path.join(__dirname, `.ai_receipt_w77_review_${process.pid}.cjs`);
try { fs.writeFileSync(temporaryHarness, extended); } catch (e) { throw new Error(`could not create transient review harness: ${e.message}`); }
try {
  const run = spawnSync(process.execPath, [temporaryHarness, controllerPath, explainerPath], { cwd: process.cwd(), encoding: 'utf8' });
  assert.equal(run.status, 0, run.stderr || run.stdout || 'actual W77 route harness failed');
  console.log(JSON.stringify({
    status: 'PASS_WITH_LIMITS',
    freshCases: 3,
    originalHarness: 'tests/ai_receipt_explainer_w77_contract.cjs (unchanged; 6 positive and 5 negative phrase checks plus route cases)',
    checks: ['revision-changing apply refreshes receipt ticket', 'new failed-only receipt supersedes old success in explanation', 'mixed action stays on actual action route'],
    controllerSha256: pins.get(controllerPath),
    explainerSha256: pins.get(explainerPath),
    limitations: ['Uses the original harness controlled applyQueue/document/Undo stubs; no native editor, live server, or provider.', 'Does not claim visual correctness of paint output.']
  }, null, 2));
} finally { try { fs.unlinkSync(temporaryHarness); } catch (_) {} }
