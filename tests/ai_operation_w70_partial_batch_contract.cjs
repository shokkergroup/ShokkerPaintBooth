'use strict';
// W70 desired outcomes frozen before inspecting real ZoneKit/tool/batch implementations.
const cases = Object.freeze([
  { id: 'valid-single-operation', expected: 'one-success-line-and-undo' },
  { id: 'valid-multi-operation', expected: 'all-ops-applied-and-complete-claim' },
  { id: 'later-invalid-in-route-generated-batch', expected: 'zero-mutation-or-explicit-partial-result' },
  { id: 'duplicate-or-missing-target-in-batch', expected: 'refuse-ambiguous-operation-without-claiming-it' },
  { id: 'malformed-add-after-valid-edit', expected: 'atomic-refusal-or-truthful-partial-result' },
  { id: 'invalid-edit-after-valid-add', expected: 'atomic-refusal-or-truthful-partial-result' },
  { id: 'local-commit-exception-after-first-op', expected: 'truthful-partial-state-with-no-full-success-claim' },
  { id: 'offline-multi-op-route', expected: 'same-batch-result-truthfulness-as-normal-route' },
  { id: 'MCP-multi-op-route', expected: 'same-batch-result-truthfulness-as-normal-route' },
  { id: 'single-zonekit-op-validation-failure', expected: 'no-mutation-and-clear-failure' },
  { id: 'rejected-compile-does-not-touch-existing-zone', expected: 'zero-queue-zero-mutation' },
  { id: 'partial-success-never-overstates-aggregate', expected: 'reply-identifies-only-successful-operations' }
]);
if (cases.length < 12) throw new Error('W70 requires at least 12 frozen outcomes');
module.exports = { cases };
