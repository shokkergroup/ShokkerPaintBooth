// Independent W8 contract cases authored before inspecting js/spb-ai-material-controls.js.
// This review intentionally exercises parser meaning and the spec-shift builder boundary.
const CASES = [
  { id: 'point-lower', text: 'Lower clearcoat on the roof by 12 points.', intent: ['clearcoat', 'roof', -12, 'points'] },
  { id: 'point-raise', text: 'Increase metalness on the hood by 8 points.', intent: ['metalness', 'hood', 8, 'points'] },
  { id: 'relative-percent-lower', text: 'Lower clearcoat on the roof by 10 percent.', reject: true },
  { id: 'relative-percent-raise', text: 'Raise roughness on the door by 7%.', reject: true },
  { id: 'direction-required', text: 'Change clearcoat on the roof by 6 points.', reject: true },
  { id: 'diagnostic-preface', text: 'Everything is too shiny; lower clearcoat on the roof by 12 points.', intent: ['clearcoat', 'roof', -12, 'points'] },
  { id: 'native-c07-wording', text: 'Everything is too shiny; lower clearcoat on roof only.', intent: ['clearcoat', 'roof', -20, 'points'] },
  { id: 'diagnostic-only', text: 'The clearcoat on the roof is too shiny.', reject: true },
  { id: 'mixed-extra-action', text: 'Lower clearcoat on the roof by 10 points and make it look like Flame Lapped Clearcoat.', reject: true },
  { id: 'two-material-actions', text: 'Lower clearcoat on the roof by 10 points and increase metallic on the hood by 4 points.', reject: true },
  { id: 'number-not-amount', text: 'Lower clearcoat on roof 2.', reject: true },
  { id: 'part-name-substring', text: 'Lower clearcoat on the rooftop decal by 10 points.', reject: true },
  { id: 'zone-word-alone', text: 'Lower clearcoat by 10 points.', reject: true },
  { id: 'missing-zone-id', text: 'Lower clearcoat on the roof by 10 points.', zone: { name: 'Roof', id: null }, rejectBuild: true },
  { id: 'missing-zone-name', text: 'Lower clearcoat on the roof by 10 points.', zone: { name: '', id: 'roof-1' }, rejectBuild: true },
  { id: 'point-over-bound', text: 'Lower clearcoat on the roof by 256 points.', intent: ['clearcoat', 'roof', -256, 'points'] },
  { id: 'percent-over-bound', text: 'Lower clearcoat on the roof by 101%.', reject: true },
  { id: 'zero-noop', text: 'Lower clearcoat on the roof by 0 points.', intent: ['clearcoat', 'roof', -0, 'points'] },
  { id: 'channel-sign-roughness', text: 'Lower roughness on the hood by 9 points.', intent: ['roughness', 'hood', -9, 'points'] },
  { id: 'channel-sign-metalness', text: 'Raise metalness on the roof by 9 points.', intent: ['metalness', 'roof', 9, 'points'] },
  { id: 'absolute-level-language', text: 'Set clearcoat on the roof to 20 points.', reject: true },
  { id: 'absolute-level-percent', text: 'Set clearcoat on the roof to 20%.', reject: true },
  { id: 'missing-amount', text: 'Lower clearcoat on the roof.', intent: ['clearcoat', 'roof', -20, 'points'] },
  { id: 'negative-input', text: 'Lower clearcoat on the roof by -10 points.', reject: true },
  { id: 'extra-number', text: 'Lower clearcoat on the roof by 10 points, then set strength to 80.', reject: true },
];

// Post-inspection supplemental cases requested by the parent; not part of the fresh oracle.
const SUPPLEMENTAL_AFTER_INSPECTION = [
  { id: 'absolute-point-target-under-lower-verb', text: 'Lower clearcoat on the roof to 40 points.', reject: true },
  { id: 'dangling-target-number', text: 'Lower clearcoat on the roof 40 points.', reject: true },
  { id: 'trailing-word-after-relative-amount', text: 'Lower clearcoat on the roof by 10 points please.', reject: true },
  { id: 'amount-followed-by-extra-target-words', text: 'Lower clearcoat on the roof by 10 points from the front.', reject: true },
  { id: 'only-after-relative-amount', text: 'Lower clearcoat on the roof by 10 points only.', reject: true },
];

const assert = require('node:assert/strict');
const controls = require('../js/spb-ai-material-controls.js');
assert.equal(typeof controls.parse, 'function');
assert.equal(typeof controls.buildEdit, 'function');

let passed = 0;
const failures = [];
for (const c of CASES) {
  const parsed = controls.parse(c.text);
  if (c.rejectBuild) {
    try {
      assert.equal(parsed.kind, 'edit', `${c.id}: parse kind`);
      const out = controls.buildEdit(c.zone, parsed);
      assert.equal(out.kind, c.zone.id == null ? 'invalid' : 'edit', `${c.id}: zone validation`);
      passed++;
    } catch (e) { failures.push(e.message); }
  } else if (c.reject) {
    try { assert.notEqual(parsed.kind, 'edit', `${c.id} must not become an edit`); passed++; }
    catch (e) { failures.push(e.message); }
  } else {
    try {
      assert.equal(parsed.kind, 'edit', `${c.id}: parse kind`);
      assert.equal(parsed.channel, c.intent[0], `${c.id}: channel`);
      assert.equal(parsed.part, c.intent[1], `${c.id}: part`);
      assert.equal(parsed.delta, c.intent[2], `${c.id}: signed amount`);
      assert.equal(parsed.amountUnit || 'points', c.intent[3], `${c.id}: amount unit`);
      passed++;
    } catch (e) { failures.push(e.message); }
  }
}
try {
  assert.equal(controls.parse('Lower clearcoat on the roof by 12 points.').amountSpecified, true, 'explicit amount marker');
  assert.equal(controls.parse('Lower clearcoat on the roof.').amountSpecified, false, 'default amount marker');
  passed++;
} catch (e) { failures.push(e.message); }

let supplementalPassed = 0;
const supplementalFailures = [];
for (const c of SUPPLEMENTAL_AFTER_INSPECTION) {
  try {
    const parsed = controls.parse(c.text);
    if (c.reject) assert.notEqual(parsed.kind, 'edit', `${c.id} must not become an edit`);
    supplementalPassed++;
  } catch (e) { supplementalFailures.push(e.message); }
}

function buildCase(label, zone, parsed, expectedKind, expectedShift, expectedReason) {
  try {
    const before = JSON.parse(JSON.stringify(zone));
    const out = controls.buildEdit(zone, parsed);
    assert.equal(out.kind, expectedKind, `${label}: result kind`);
    if (expectedReason) assert.equal(out.reason, expectedReason, `${label}: reason`);
    if (expectedShift) {
      assert.deepEqual(out.spec_shift, expectedShift, `${label}: complete spec tuple`);
      assert.equal(typeof out.zone_id, 'string', `${label}: zone id`);
      assert.deepEqual(Object.keys(out).sort(), (zone.name != null ? ['expect_name', 'kind', 'spec_shift', 'zone_id'] : ['kind', 'spec_shift', 'zone_id']).sort(), `${label}: no unrelated fields`);
    }
    assert.deepEqual(zone, before, `${label}: zone input is immutable`);
    passed++;
  } catch (e) { failures.push(e.message); }
}

const zone = { id: 'roof-7', name: 'Roof', specShiftR: 11, specShiftG: 22, specShiftB: 33, finish: 'KeepMe', color: '#123456' };
buildCase('clearcoat maps B and accumulates', zone, { kind: 'edit', channel: 'clearcoat', delta: -12 }, 'edit', { metal: 11, rough: 22, clearcoat: 21 });
buildCase('metalness maps R and accumulates', zone, { kind: 'edit', channel: 'metalness', delta: 8 }, 'edit', { metal: 19, rough: 22, clearcoat: 33 });
buildCase('roughness maps G and accumulates', zone, { kind: 'edit', channel: 'roughness', delta: -9 }, 'edit', { metal: 11, rough: 13, clearcoat: 33 });
buildCase('clamps upper bound', { id: 'z', specShiftR: 120, specShiftG: 0, specShiftB: 0 }, { kind: 'edit', channel: 'metalness', delta: 50 }, 'edit', { metal: 127, rough: 0, clearcoat: 0 });
buildCase('clamps lower bound', { id: 'z', specShiftR: -120, specShiftG: 0, specShiftB: 0 }, { kind: 'edit', channel: 'metalness', delta: -50 }, 'edit', { metal: -127, rough: 0, clearcoat: 0 });
buildCase('large point request clamps tuple', { id: 'z', specShiftR: 0, specShiftG: 0, specShiftB: 0 }, { kind: 'edit', channel: 'clearcoat', delta: -256 }, 'edit', { metal: 0, rough: 0, clearcoat: -127 });
buildCase('limit becomes noop', { id: 'z', specShiftR: 127 }, { kind: 'edit', channel: 'metalness', delta: 1 }, 'noop', null, 'channel-already-at-limit');
buildCase('zero is noop', { id: 'z' }, { kind: 'edit', channel: 'clearcoat', delta: 0 }, 'noop', null, 'zero-adjustment');
buildCase('missing zone', null, { kind: 'edit', channel: 'clearcoat', delta: -1 }, 'invalid', null, 'real-zone-id-required');
buildCase('missing zone id', { name: 'Roof' }, { kind: 'edit', channel: 'clearcoat', delta: -1 }, 'invalid', null, 'real-zone-id-required');
buildCase('zone without name still builds', { id: 'roof-7' }, { kind: 'edit', channel: 'clearcoat', delta: -1 }, 'edit', { metal: 0, rough: 0, clearcoat: -1 });
buildCase('target-to-zone identity is parent responsibility', { id: 'roof-7', name: 'Roof' }, { kind: 'edit', channel: 'clearcoat', part: 'rooftop decal', delta: -1 }, 'edit', { metal: 0, rough: 0, clearcoat: -1 });
buildCase('non-edit parse', { id: 'z' }, { kind: 'clarify' }, 'invalid', null, 'parsed-edit-required');
buildCase('unsupported channel', { id: 'z' }, { kind: 'edit', channel: 'shine', delta: 1 }, 'invalid', null, 'unsupported-channel-or-delta');

if (failures.length) {
  console.error(`FRESH/BASELINE FAIL ${passed}/${CASES.length + 15} checks; ${failures.length} failure(s)`);
  failures.forEach(f => console.error(`- ${f}`));
  process.exitCode = 1;
} else {
  console.log(`PASS ${passed}/${CASES.length + 15} fresh/baseline material-control checks`);
}
if (supplementalFailures.length) {
  console.error(`POST-INSPECTION SUPPLEMENTAL FAIL ${supplementalPassed}/${SUPPLEMENTAL_AFTER_INSPECTION.length}; ${supplementalFailures.length} failure(s)`);
  supplementalFailures.forEach(f => console.error(`- ${f}`));
  process.exitCode = 1;
} else console.log(`PASS ${supplementalPassed}/${SUPPLEMENTAL_AFTER_INSPECTION.length} post-inspection supplemental syntax checks`);

module.exports = { CASES, SUPPLEMENTAL_AFTER_INSPECTION };
