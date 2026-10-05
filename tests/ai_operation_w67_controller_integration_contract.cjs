'use strict';
// W67 fresh route/controller oracle, frozen before inspecting ask/send/finish bodies.
const cases = Object.freeze([
  { id: 'uncommitted-post-draw-ask', expected: 'refusal-no-queue-no-done' },
  { id: 'uncached-hash-throws', expected: 'refusal-no-queue-no-done' },
  { id: 'uncached-hash-empty', expected: 'refusal-no-queue-no-done' },
  { id: 'uncached-hash-missing', expected: 'refusal-no-queue-no-done' },
  { id: 'source-pending-at-publication', expected: 'refusal-no-queue-no-done' },
  { id: 'retained-source-after-failed-replacement', expected: 'normal-positive-edit' },
  { id: 'current-source-valid-queue-and-finish', expected: 'exactly-one-queue-and-honest-finish' },
  { id: 'refusal-releases-busy-and-lease', expected: 'settled-and-released' },
  { id: 'passive-howto-without-source', expected: 'guidance-available-no-provider' },
  { id: 'controller-apply-error', expected: 'honest-error-no-done' },
  { id: 'refusal-does-not-add-undo-entry', expected: 'undo-unchanged' },
  { id: 'provider-boundary', expected: 'zero-provider-calls' }
]);
if (cases.length < 12) throw new Error('W67 oracle requires at least 12 fresh cases');
module.exports = { cases };
