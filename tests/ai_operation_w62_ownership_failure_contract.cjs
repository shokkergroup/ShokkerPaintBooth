// W62 fresh fail-closed oracle, frozen before inspecting Gen3 candidate code.
const cases = Object.freeze([
  { id: 'missing-zone-hash-getter-after-manual-change', expected: 'no-apply' },
  { id: 'zone-hash-getter-throws-after-manual-change', expected: 'no-apply' },
  { id: 'zone-hash-getter-throws-at-apply-boundary', expected: 'no-apply' },
  { id: 'missing-zone-hash-getter-with-stale-revision', expected: 'no-apply' },
  { id: 'failed-source-replacement-retains-old-pixels', expected: 'no-apply' },
  { id: 'failed-source-replacement-with-stale-document-token', expected: 'no-apply' },
  { id: 'source-is-currently-loading', expected: 'no-apply' },
  { id: 'source-ready-with-current-zone-hash', expected: 'apply-once' },
  { id: 'cached-zone-hash-is-not-authoritative-at-apply', expected: 'no-apply-after-mutation' },
  { id: 'whole-body-document-swap', expected: 'no-apply' },
  { id: 'non-edit-help-does-not-queue', expected: 'no-queue' },
  { id: 'no-paint-help-remains-passive', expected: 'passive-help' }
]);
if (cases.length < 12) throw new Error('W62 oracle requires at least 12 fresh cases');
module.exports = { cases };
