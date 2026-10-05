'use strict';
const assert = require('node:assert/strict');
const controls = require('../js/spb-ai-material-controls.js');

const cases = [
  ['diagnostic prefix and default down', 'Everything is too shiny; lower clearcoat on the roof only.', 'edit', 'clearcoat', 'roof', -20],
  ['metalness up', 'Raise the metalness on the hood.', 'edit', 'metalness', 'hood', 20],
  ['roughness down by points', 'Reduce roughness by 12 points on the right side panel.', 'edit', 'roughness', 'right side', -12],
  ['clearcoat up explicit points', 'Increase clearcoat on the roof by 5 points.', 'edit', 'clearcoat', 'roof', 5],
  ['diagnostic prose comma', 'The roof looks too glossy, decrease clearcoat on the roof.', 'edit', 'clearcoat', 'roof', -20],
  ['specific panel identity', 'Lower metallic channel on the left side panel by 9 points.', 'edit', 'metalness', 'left side', -9],
  ['clearcoat synonym', 'Lower clear coat on rear bumper by 8 points.', 'edit', 'clearcoat', 'rear bumper', -8],
  ['roughness full channel synonym', 'Raise roughness channel by 3 points on the trunk.', 'edit', 'roughness', 'trunk', 3],
  ['amount after target', 'Increase metalness on the roof by 14 points.', 'edit', 'metalness', 'roof', 14],
  ['leading please and bonnet synonym', 'Please lower roughness on the bonnet by 10 points.', 'edit', 'roughness', 'hood', -10],
  ['default delta on spoiler', 'Decrease clearcoat on the spoiler.', 'edit', 'clearcoat', 'spoiler', -20],
];
for (const [label, text, kind, channel, part, delta] of cases) {
  const p = controls.parse(text);
  assert.equal(p.kind, kind, `${label}: ${JSON.stringify(p)}`);
  assert.equal(p.channel, channel, label);
  assert.equal(p.part, part, label);
  assert.equal(p.delta, delta, label);
}
const rejected = [
  ['absolute percent is not an offset', 'Set clearcoat to 70% on the roof.', 'absolute-percent-is-not-a-relative-shift'],
  ['relative percent needs explicit points', 'Lower clearcoat by 20% on the roof.', 'relative-amount-needs-points'],
  ['material channel asks which channel', 'Lower the material channel on the roof.', 'ambiguous-channel'],
  ['vague shine channel asks', 'Lower the shine on the roof.', 'ambiguous-channel'],
  ['missing part asks', 'Raise clearcoat by 10 points.', 'missing-exact-part'],
  ['whole-car scope rejected', 'Lower clearcoat on the whole car.', 'broad-or-ambiguous-part'],
  ['generic panel scope rejected', 'Lower roughness on the side.', 'broad-or-ambiguous-part'],
  ['multiple targets rejected', 'Lower clearcoat on the roof and hood.', 'mixed-or-unsupported-edit'],
  ['mixed recolor refused', 'Lower clearcoat on the roof and make it blue.', 'mixed-or-unsupported-edit'],
  ['finish change refused', 'Raise roughness on the roof and make it matte.', 'mixed-or-unsupported-edit'],
  ['multiple channels refused', 'Lower roughness and clearcoat on the roof.', 'mixed-or-unsupported-edit'],
  ['question delegates', 'Why is clearcoat high on the roof?', 'question-or-howto'],
  ['howto delegates', 'How do I lower clearcoat on the roof?', 'question-or-howto'],
  ['negative delegates', "Don't lower clearcoat on the roof.", 'negative-or-prohibition'],
  ['negative numeric amount rejected', 'Lower clearcoat on the roof by -10 points.', 'negative-relative-amount'],
  ['numeric target suffix rejected', 'Lower clearcoat on roof 2.', 'unconsumed-number-in-target'],
  ['substring target rejected', 'Lower clearcoat on the rooftop decal by 10 points.', 'unsupported-or-ambiguous-part'],
  ['absolute point target rejected', 'Lower clearcoat on the roof to 40 points.', 'absolute-points-is-not-a-relative-shift'],
  ['dangling points rejected', 'Lower clearcoat on the roof 40 points.', 'unconsumed-number-in-target'],
  ['trailing please rejected', 'Lower clearcoat on the roof by 10 points please.', 'unconsumed-number-in-target'],
  ['extra target words rejected', 'Lower clearcoat on the roof by 10 points from the front.', 'unconsumed-number-in-target'],
  ['only after amount rejected', 'Lower clearcoat on the roof by 10 points only.', 'unconsumed-words-after-amount'],
  ['non-command delegates', 'The roof is too shiny.', 'no-explicit-channel-adjustment'],
];
for (const [label, text, reason] of rejected) {
  const p = controls.parse(text);
  assert.notEqual(p.kind, 'edit', `${label} must not create an edit`);
  const delegates = /^(question|howto|negative delegates|non-command)/.test(label);
  assert.equal(p.kind, delegates ? 'delegate' : 'clarify', `${label}: ${JSON.stringify(p)}`);
  if (delegates) assert.equal(p.reason, reason, label);
}

const original = { id: 'zone-7', name: 'Red roof', specShiftR: 11, specShiftG: -4, specShiftB: 50,
  base: 'base::f_soft_gloss', baseColor: '#c8102e', pattern: { id: 'p1' }, regionMask: new Uint8Array([1, 0, 1]) };
const snapshot = { r: original.specShiftR, g: original.specShiftG, b: original.specShiftB, base: original.base,
  color: original.baseColor, pattern: JSON.stringify(original.pattern), mask: Array.from(original.regionMask) };
const built = controls.buildEdit(original, { kind: 'edit', channel: 'clearcoat', delta: -20 });
assert.equal(built.kind, 'edit');
assert.deepEqual(built.spec_shift, { metal: 11, rough: -4, clearcoat: 30 });
assert.equal(built.zone_id, 'zone-7'); assert.equal(built.expect_name, 'Red roof');
assert.deepEqual({ r: original.specShiftR, g: original.specShiftG, b: original.specShiftB, base: original.base,
  color: original.baseColor, pattern: JSON.stringify(original.pattern), mask: Array.from(original.regionMask) }, snapshot,
  'builder is pure and leaves finish, color, pattern, mask and zone channels untouched');
assert.deepEqual(controls.buildEdit({ id: 'c', specShiftR: 120 }, { kind: 'edit', channel: 'metalness', delta: 20 }).spec_shift,
  { metal: 127, rough: 0, clearcoat: 0 }, 'positive cap is clamped');
assert.deepEqual(controls.buildEdit({ id: 'c', specShiftG: -120 }, { kind: 'edit', channel: 'roughness', delta: -20 }).spec_shift,
  { metal: 0, rough: -127, clearcoat: 0 }, 'negative cap is clamped');
assert.equal(controls.buildEdit({ id: 'c', specShiftB: 127 }, { kind: 'edit', channel: 'clearcoat', delta: 20 }).kind, 'noop', 'clamped no-op is surfaced');
assert.equal(controls.buildEdit({ id: 'c' }, { kind: 'edit', channel: 'clearcoat', delta: 0 }).kind, 'noop');
assert.equal(controls.buildEdit({ name: 'No ID' }, { kind: 'edit', channel: 'roughness', delta: 5 }).reason, 'real-zone-id-required');
assert.equal(controls.buildEdit({ id: 'c' }, { kind: 'edit', channel: 'color', delta: 5 }).kind, 'invalid');

console.log(`PASS ${cases.length} explicit parser cases, ${rejected.length} safe non-edit cases, and 7 pure builder bounds/immutability cases`);
