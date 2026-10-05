'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('js/spb-pro-ai.js', 'utf8');
const startMarker = '// ELEMENT_REPLY_ROUTING_HELPERS_START';
const endMarker = '// ELEMENT_REPLY_ROUTING_HELPERS_END';
const start = source.indexOf(startMarker);
const end = source.indexOf(endMarker, start);
assert(start >= 0 && end > start, 'element reply routing helper block is present');
const helperSource = source.slice(start + startMarker.length, end);
const context = {};
vm.runInNewContext(`${helperSource}\nthis.route = { elemCurrentCard, elemReplyAction, dispatchElemCardAction, dispatchElemTeach, elementRunResult, elementFinishGuard, elementRestoreGuard, dispatchElementTool, elementPaintChangedResult };`, context);

const card = (id, mode = 'confirm', sig = 'paint-a', done = false, kind = 'numbers') => ({
  role: 'ai', id, elem: { kind, mode, sig, done, identity: `${sig}|car=car-a|layers=1` }
});

const old = card(1, 'confirm', 'paint-a');
const stale = card(2, 'confirm', 'paint-old');
const current = card(3, 'confirm', 'paint-a');
const done = card(4, 'confirm', 'paint-a', true);
assert.equal(context.route.elemCurrentCard([done, old, stale, current], 'paint-a'), current,
  'uses the latest unfinished card that belongs to the current paint');
assert.equal(context.route.elemCurrentCard([old, stale], 'paint-b'), null,
  'ignores cards left from another paint');
assert.equal(context.route.elemCurrentCard([old], ''), null,
  'does not guess when the current paint has no identity');

const identity = current.elem.identity;
let yesCalls = 0, teachCalls = 0;
const actions = { yes: () => { yesCalls++; }, none: () => {}, no: () => {} };
assert.equal(context.route.dispatchElemCardAction(stale, 'elemyes', [old, stale], 'paint-a', identity, actions), false,
  'a stale card button cannot dispatch against the current paint');
assert.equal(yesCalls, 0, 'a stale confirm does not rerun the old request');
assert.equal(context.route.dispatchElemCardAction(current, 'elemyes', [old, current], 'paint-a', identity, actions), true,
  'the current confirm button dispatches');
assert.equal(yesCalls, 1, 'the current confirm invokes its action once');
assert.equal(context.route.dispatchElemTeach(stale, [stale], 'paint-a', identity, () => { teachCalls++; }), false,
  'a stale teach canvas cannot call El.teach');
assert.equal(teachCalls, 0, 'the stale teach callback remains untouched');
assert.equal(context.route.dispatchElemTeach(current, [current], 'paint-a', identity, () => { teachCalls++; }), true,
  'the current teach canvas dispatches');
assert.equal(teachCalls, 1, 'the current teach callback runs once');

const olderSamePaint = card(6, 'confirm', 'paint-a');
const newerCompleted = card(7, 'confirm', 'paint-a', true);
assert.equal(context.route.elemCurrentCard([olderSamePaint, newerCompleted], 'paint-a'), null,
  'a completed newer card does not revive an older unfinished card');
assert.equal(context.route.dispatchElemCardAction(olderSamePaint, 'elemyes', [olderSamePaint, newerCompleted], 'paint-a', identity, actions), false,
  'an older same-paint button stays blocked after the newer card completes');
assert.equal(yesCalls, 1, 'a superseded card cannot dispatch its action');

assert.equal(context.route.elemReplyAction('yes, those are them', current), 'elemyes');
assert.equal(context.route.elemReplyAction('yes', current), 'elemyes');
assert.equal(context.route.elemReplyAction('no', current), 'elemno');
assert.equal(context.route.elemReplyAction('no, I will show you', current), 'elemno');
assert.equal(context.route.elemReplyAction('no, these are wrong', current), 'elemno');
assert.equal(context.route.elemReplyAction('no, those are wrong', current), 'elemno');
assert.equal(context.route.elemReplyAction('no, that is not right', current), 'elemno');
assert.equal(context.route.elemReplyAction('No, that is wrong', current), 'elemno');
assert.equal(context.route.elemReplyAction('No, that\'s wrong', current), 'elemno');
assert.equal(context.route.elemReplyAction('No, that\'s not right', current), 'elemno');
assert.equal(context.route.elemReplyAction('No, those aren\'t right', current), 'elemno');
assert.equal(context.route.elemReplyAction('No, this is wrong', current), 'elemno');
assert.equal(context.route.elemReplyAction('No, this is not right', current), 'elemno');
assert.equal(context.route.elemReplyAction('No, I will show you the numbers', current), 'elemno');
assert.equal(context.route.elemReplyAction('No, I will show you the sponsors', current), null);
assert.equal(context.route.elemReplyAction('No, I will show you the stripes', current), null);
assert.equal(context.route.elemReplyAction('No, I will show you the numbers and sponsors', current), null);
assert.equal(context.route.elemReplyAction('No, I will show you the numbers', card(12, 'confirm', 'paint-a', false, 'sponsors')), null);
assert.equal(context.route.elemReplyAction('No, I will show you the logos', card(13, 'confirm', 'paint-a', false, 'sponsors')), 'elemno');
assert.equal(context.route.elemReplyAction('yes those are numbers', current), 'elemyes');
assert.equal(context.route.elemReplyAction('yes those are sponsors', current), null,
  'a named yes must match the card kind');
assert.equal(context.route.elemReplyAction('yes, those are sponsors', card(8, 'confirm', 'paint-a', false, 'sponsors')), 'elemyes');
assert.equal(context.route.elemReplyAction('yes those are stripes', card(10, 'confirm', 'paint-a', false, 'stripes')), 'elemyes');
assert.equal(context.route.elemReplyAction('there are none on this paint', current), 'elemnone');
assert.equal(context.route.elemReplyAction('no, there are none on this paint', current), 'elemnone');
assert.equal(context.route.elemReplyAction('there are no numbers', current), 'elemnone');
assert.equal(context.route.elemReplyAction('there are no sponsors', current), null,
  'a named none reply cannot close a different element kind');
assert.equal(context.route.elemReplyAction('there are no sponsors', card(11, 'confirm', 'paint-a', false, 'sponsors')), 'elemnone');
assert.equal(context.route.elemReplyAction('yes, those are them', card(5, 'teach')), null,
  'yes cannot confirm a teach card');
assert.equal(context.route.elemReplyAction('no', card(9, 'teach')), null,
  'plain no does not restart a teach card');
assert.equal(context.route.elemReplyAction('yes, those are them', null), null,
  'an unbound yes has no action');
assert.equal(context.route.elemReplyAction('yes', null), null,
  'plain yes without an active card is unclaimed');
assert.equal(context.route.elemReplyAction('no', null), null,
  'plain no without an active card is unclaimed');
assert.equal(context.route.elemReplyAction('no, use matte instead', current), null,
  'negative design instructions are not card replies');
assert.equal(context.route.elemReplyAction('no chrome, no stripes', current), null,
  'unrelated negative design orders remain unclaimed');
assert.equal(context.route.elemReplyAction('what does this button do?', current), null,
  'ordinary questions do not become element replies');

assert.match(source, /function elemOwnsText\(t\) \{ return NOT_ELEM_RE\.test\(t\); \}/,
  'old pending cards do not suppress unrelated self-help');
assert.match(source, /function offlineElemWrong\(text, word\)/,
  'the existing wrong-element teach route remains installed');
assert.match(source, /else if \(act === 'elemyes' \|\| act === 'elemnone' \|\| act === 'elemno'\) runElemAction\(ent, act\)/,
  'card buttons use the shared element action handler');
assert.match(source, /if \(replyAct && runElemAction\(replyCard, replyAct\)\) return;/,
  'typed replies use that same action handler');
assert.match(source, /function runElemAction\(ent, act\) \{\s*return dispatchElemCardAction\(ent, act, _log, elementPaintSig\(\),/,
  'button and typed actions both pass through the live paint guard');
assert.match(source, /dispatchElemTeach\(m, _log, elementPaintSig\(\), elementRunIdentity\(\), function \(\)/,
  'canvas teaching uses the same live paint guard');
assert.match(source, /function restorePreviewSnapshot\(\) \{\s*if \(entry\.elementRunIdentity\) return elementRestoreGuard\(entry\.elementRunIdentity, elementRunIdentity, function \(\) \{ restoreZones\(snap, sel\); \}\);/,
  'element option previews restore snapshots only through the identity guard');
assert.match(source, /if \(stalePreview \|\| \(entry\.elementRunIdentity && !elementRunCurrent\(entry\.elementRunIdentity\)\)\) return staleOptionRun\(\);\s*if \(!restorePreviewSnapshot\(\)\) return staleOptionRun\(\);/,
  'preview settlement and rejection check identity before restoring old zones');

const reviewStart = source.indexOf('    function postCheck(');
const reviewEnd = source.indexOf('    // ------------------------------------------------------------------ PANEL PICKER', reviewStart);
assert(reviewStart >= 0 && reviewEnd > reviewStart, 'real postCheck and finalVerdict source is available');
const reviewSource = source.slice(reviewStart, reviewEnd);
const cancelStart = source.indexOf('    function elementRunCanceled()');
const cancelEnd = source.indexOf('\n', cancelStart);
assert(cancelStart >= 0 && cancelEnd > cancelStart, 'real element cancellation cleanup is available');
const cancelSource = source.slice(cancelStart, cancelEnd);
function makeReviewHarness(options = {}) {
  const review = {
    liveIdentity: identity,
    settle: options.settle || null,
    criticDeferred: options.criticDeferred || null,
    criticCalls: 0,
    repairCalls: 0,
    applyCalls: 0,
    undoCalls: 0,
    cancelCalls: 0,
    renders: 0,
    _busy: false,
    _progress: '',
    _ctl: { active: true },
    _noCheck: false,
    _extra: { cost: 0, calls: 0 },
    _beforeImg: null,
    window: { SPB_AI_KEEP: false },
    Z: {
      whenSettled: () => review.settle ? review.settle.promise : Promise.resolve(),
      previewImage: () => 'live-preview'
    },
    D: { compoundPlan: () => null },
    CAR: { hasParts: () => false },
    render: () => { review.renders++; },
    elementRunCurrent: captured => captured === review.liveIdentity,
    elementFinishGuard: (captured, read, apply) => { if (!captured || read() !== captured) return false; apply(); return true; },
    previewPalette: () => Promise.resolve({}),
    finishOnlyQueue: () => false,
    intentSpecOnly: () => false,
    panelsNeeded: () => [],
    wantedColours: () => [],
    topBin: () => ({ name: 'red', pct: 50 }),
    zoneColourProblems: () => Promise.resolve([]),
    paintDiffAsync: () => Promise.resolve(0),
    critic: () => {
      review.criticCalls++;
      if (review.criticDeferred && review.criticCalls === 1) return review.criticDeferred.promise;
      if (options.matchingRepair && review.criticCalls === 1) return Promise.resolve({ score: 2, problems: ['wrong paint'] });
      return Promise.resolve({ score: 9, problems: [] });
    },
    elementRunIdentity: () => review.liveIdentity,
    escModel: () => null,
    runTurn: () => { review.repairCalls++; return Promise.resolve({ usage: {}, queue: [{ kind: 'add' }], text: 'repaired' }); },
    applyQueue: () => { review.applyCalls++; return { maskUndo: null, lines: ['repair applied'], failed: [] }; },
    mergeMaskUndo: () => {},
    doUndo: () => { review.undoCalls++; },
    bump: () => {},
    cost: () => 'cost',
    finishMeta: undefined,
    HIST: [],
    _log: []
  };
  vm.runInNewContext(`${cancelSource}\n${reviewSource}\nthis.reviewApi = { postCheck, finalVerdict };`, review);
  return review;
}
assert.match(source, /!elemCardIsCurrent\(m, _log, elementPaintSig\(\), elementRunIdentity\(\)\)\) return; cv\._bound/,
  'stale element cards are not initialized for interaction');

(async function () {
  const deferred = () => {
    let resolve;
    const promise = new Promise(r => { resolve = r; });
    return { promise, resolve };
  };
  let liveIdentity = identity, toolMutations = 0, finishMutations = 0, toolCalls = 0;
  let acceptedIdentity = null;
  assert.equal(context.route.dispatchElemCardAction(current, 'elemyes', [old, current], 'paint-a', identity, {
    yes: entry => { acceptedIdentity = entry.elem.identity; }
  }), true, 'accepts the current card before starting its rerun');
  const pendingTool = deferred();
  const toolResult = context.route.dispatchElementTool(acceptedIdentity, () => liveIdentity, () => {
    toolCalls++;
    return pendingTool.promise.then(() => {
      const allowed = context.route.elementFinishGuard(acceptedIdentity, () => liveIdentity, () => { toolMutations++; });
      return allowed ? { queue: [{ kind: 'edit' }] } : context.route.elementPaintChangedResult();
    });
  });
  assert.equal(toolCalls, 1, 'dispatches the current rerun tool once');
  liveIdentity = identity.replace('layers=1', 'layers=2');
  pendingTool.resolve({ queue: [{ kind: 'edit' }] });
  const stopped = await context.route.elementRunResult(toolResult, acceptedIdentity, () => liveIdentity);
  assert.equal(stopped.elementPaintChanged, true, 'a paint revision change cancels the deferred result');
  assert.equal(context.route.elementFinishGuard(acceptedIdentity, () => liveIdentity, () => { finishMutations++; }), false,
    'the stale completion cannot enter the finish/apply callback');
  assert.equal(toolMutations, 0, 'the async tool continuation cannot mutate the changed paint');
  assert.equal(finishMutations, 0, 'no queued mutation is applied after the paint changes');

  const currentIdentity = liveIdentity;
  const normalTool = context.route.dispatchElementTool(currentIdentity, () => liveIdentity, () => Promise.resolve().then(() => {
    const allowed = context.route.elementFinishGuard(currentIdentity, () => liveIdentity, () => { toolMutations++; });
    return allowed ? { queue: [{ kind: 'edit' }] } : context.route.elementPaintChangedResult();
  }));
  const normalResult = await context.route.elementRunResult(normalTool, currentIdentity, () => liveIdentity);
  assert.equal(normalResult.elementPaintChanged, undefined, 'a current rerun keeps its tool result');
  assert.equal(context.route.elementFinishGuard(currentIdentity, () => liveIdentity, () => { finishMutations++; }), true,
    'a current rerun reaches finish/apply');
  assert.equal(toolMutations, 1, 'the current rerun executes its async tool once');
  assert.equal(finishMutations, 1, 'the current rerun applies once');
  assert.equal(toolCalls, 1, 'the stale request does not dispatch additional tools');

  let settledIdentity = identity, restores = 0;
  const optionSettled = deferred();
  const optionContinuation = optionSettled.promise.then(() => context.route.elementRestoreGuard(identity, () => settledIdentity, () => { restores++; }));
  settledIdentity = identity.replace('layers=1', 'layers=2');
  optionSettled.resolve();
  assert.equal(await optionContinuation, false, 'a deferred option-settled continuation rejects stale restoration');
  assert.equal(restores, 0, 'stale option settlement never restores the prior paint zones');
  const currentOptionIdentity = settledIdentity;
  assert.equal(context.route.elementRestoreGuard(currentOptionIdentity, () => settledIdentity, () => { restores++; }), true,
    'a current option preview can restore its snapshot');
  assert.equal(restores, 1, 'the current option preview restores exactly once');

  const reviewEntry = () => ({
    elementRunIdentity: identity, lines: ['applied requested changes'], notes: [], undoable: true, undone: false,
    text: 'Applied.', _cost: 0, _calls: 1
  });
  const reviewResult = () => ({
    queue: [{ kind: 'add' }, { kind: 'edit' }], usage: { cost: 0 }, calls: 1, model: 'test', offline: false
  });
  const waitFor = async predicate => {
    for (let i = 0; i < 100 && !predicate(); i++) await new Promise(resolve => setImmediate(resolve));
    assert(predicate(), 'deferred postCheck reached the requested async boundary');
  };

  const settling = deferred();
  const duringSettle = makeReviewHarness({ settle: settling });
  const settlePromise = duringSettle.reviewApi.postCheck(reviewEntry(), 'make a red and blue paint scheme', reviewResult(), 'ask');
  duringSettle.liveIdentity = identity.replace('layers=1', 'layers=2');
  settling.resolve();
  await settlePromise;
  assert.equal(duringSettle.repairCalls, 0, 'paint change during render settlement prevents a repair turn');
  assert.equal(duringSettle.applyCalls, 0, 'paint change during render settlement prevents repair apply');
  assert.equal(duringSettle.undoCalls, 0, 'paint change during render settlement never undoes the new paint');
  assert.equal(duringSettle._busy, false, 'settlement cancellation clears chat busy state');
  assert.equal(duringSettle._progress, '', 'settlement cancellation clears progress text');
  assert.equal(duringSettle._ctl, null, 'settlement cancellation releases the active controller');
  assert.match(duringSettle._log[0].text, /paint or its layers changed/i, 'settlement cancellation explains why it stopped');

  const pendingCritic = deferred();
  const duringCritic = makeReviewHarness({ criticDeferred: pendingCritic });
  const criticPromise = duringCritic.reviewApi.postCheck(reviewEntry(), 'make a red and blue paint scheme', reviewResult(), 'ask');
  await waitFor(() => duringCritic.criticCalls === 1);
  duringCritic.liveIdentity = identity.replace('layers=1', 'layers=3');
  pendingCritic.resolve({ score: 2, problems: ['wrong paint'] });
  await criticPromise;
  assert.equal(duringCritic.repairCalls, 0, 'paint change while critic is pending prevents a repair turn');
  assert.equal(duringCritic.applyCalls, 0, 'paint change while critic is pending prevents repair apply');
  assert.equal(duringCritic.undoCalls, 0, 'paint change while critic is pending never undoes the new paint');
  assert.equal(duringCritic._busy, false, 'critic cancellation clears chat busy state');
  assert.equal(duringCritic._progress, '', 'critic cancellation clears progress text');
  assert.equal(duringCritic._ctl, null, 'critic cancellation releases the active controller');

  const matchingRepair = makeReviewHarness({ matchingRepair: true });
  await matchingRepair.reviewApi.postCheck(reviewEntry(), 'make a red and blue paint scheme', reviewResult(), 'ask');
  assert.equal(matchingRepair.repairCalls, 1, 'matching identity still runs the visual repair');
  assert.equal(matchingRepair.applyCalls, 1, 'matching identity applies the repair once');
  assert.equal(matchingRepair.undoCalls, 0, 'a successful matching repair does not undo');
  assert.equal(matchingRepair.criticCalls, 2, 'the repaired result receives its follow-up visual check');
  assert.equal(matchingRepair._busy, false, 'the successful follow-up check clears busy state');
  console.log('ai element reply contract passed');
})().catch(err => { console.error(err); process.exitCode = 1; });
