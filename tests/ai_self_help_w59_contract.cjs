// W59 desired-behavior oracle, frozen before inspecting frozen self-help bodies.
// These cases are reviewed separately from the earlier W3/W4 contracts.
const cases = Object.freeze([
  { id: 'loading-after-chip', setup: 'a Do-it action is prepared, then a new source load begins before execution', expected: 'refuse-action' },
  { id: 'failed-load-fresh-generation', setup: 'load fails but original document remains available under a fresh generation', expected: 'only-current-original-target-may-act' },
  { id: 'same-path-replaced-bytes', setup: 'selected source bytes change at the same path', expected: 'refuse-stale-target' },
  { id: 'target-moved', setup: 'target zone moves after chip preparation', expected: 'refuse-stale-target' },
  { id: 'target-renamed', setup: 'target zone is renamed after chip preparation', expected: 'refuse-stale-target' },
  { id: 'target-removed', setup: 'target zone is removed after chip preparation', expected: 'refuse-stale-target' },
  { id: 'duplicate-zone-ids', setup: 'more than one current zone has the target id', expected: 'refuse-ambiguous-target' },
  { id: 'absent-zone-id', setup: 'target zone has no stable id', expected: 'refuse-target' },
  { id: 'manual-layer-flags', setup: 'current target layer state no longer matches captured intent', expected: 'refuse-stale-target' },
  { id: 'valid-same-document-action', setup: 'same source identity and target remain current through execution', expected: 'action-only-after-controller-success' },
  { id: 'passive-help-before-paint', setup: 'no document or paint target exists', expected: 'passive-guidance-available' },
  { id: 'controller-failure-copy', setup: 'controller declines or rejects a mutating action', expected: 'never-claim-applied' }
]);
if (cases.length < 12) throw new Error('W59 oracle requires at least 12 fresh cases');
module.exports = { cases };
