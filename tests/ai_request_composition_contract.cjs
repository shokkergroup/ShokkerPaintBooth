const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const H = require('../_easy_claude_work/stack_h.js');

const w = H.load();
vm.runInContext(fs.readFileSync(path.join(H.ROOT, 'js/spb-pro-design.js'), 'utf8'), w, { filename: 'js/spb-pro-design.js' });
vm.runInContext(fs.readFileSync(path.join(H.ROOT, 'js/spb-pro-advisor.js'), 'utf8'), w, { filename: 'js/spb-pro-advisor.js' });
const D = w.SpbProDesign;
const A = w.SpbProAdvisor;

function zones(ask) {
  const plan = D.compoundPlan(ask);
  assert.ok(plan && plan.zones && plan.zones.length, `composition plan missing: ${ask}`);
  return Array.from(plan.zones);
}
function regionParts(zone) {
  if (zone.region && zone.region.everything) return ['body'];
  const part = zone.region && zone.region.part;
  return part ? (Array.isArray(part) ? Array.from(part) : [part]) : [];
}
function assertRegions(ask, expected) {
  const actual = zones(ask).map(regionParts);
  assert.deepEqual(actual, expected, ask);
}
function targetParts(value) { return Array.isArray(value) ? Array.from(value) : [value]; }

// Preservation clauses constrain scope; they do not add excluded parts to the plan.
for (const [ask, part] of [
  ['Exclusively recolor the hood matte black; keep every other panel as it is.', 'hood'],
  ['Add gold snake skin to just the roof and preserve all other paint.', 'roof'],
  ['Change the hood to blue and nothing else on the body.', 'hood'],
  ['Carbon-fiber the hood in matte blue only; do not touch the roof or sides.', 'hood'],
  ['Give the roof a matte gold carbon look, exclusively on that panel.', 'roof'],
  ['Finish everything on the roof in pearl gold, and leave the rest unchanged.', 'roof']
]) {
  const zs = zones(ask);
  assert.deepEqual(zs.map(regionParts), [[part]], `${ask}: exclusive treatment stays on its named part`);
}

// Positive body clauses remain a separate base when a later clause scopes a finish to a part.
assertRegions('Give every panel a pearl gold base, then add blue snake scales only on the roof.', [['body'], ['roof']]);
assertRegions('Set the whole-car base to pearl blue; keep that base, then add matte gold to the hood only.', [['body'], ['hood']]);
assertRegions('Keep a matte gold base on the full vehicle and use the roof layer controls for a blue carbon overlay just on the roof.', [['body'], ['roof']]);

// The advisor keeps a positive whole-car base in its tool plan, while item targets stay scoped.
{
  const ask = 'Give every panel a pearl gold base, then add blue snake scales only on the roof.';
  const plan = A.stackPlan(ask, H.ENV, { alts: 0 });
  assert.ok(plan && plan.lparts, 'body-plus-roof stack plan exists');
  assert.equal(plan.lparts.wholeBody, true, 'every-panel clause scopes the base to the body');
  const tool = A.suggestTool({ ask }, H.ENV);
  assert.match(tool.part, /body.*roof/);
  assert.deepEqual(Array.from(tool.apply.filter(s => s.tool === 'edit_zone').map(s => s.args.zone_id)).sort(), ['z5', 'z6']);
  assert.deepEqual(regionParts({ region: tool.apply.find(s => s.tool === 'add_zone').args.region }), ['roof']);
}

// Ordinary non-exclusive body + part requests still split; earlier part-only word orders remain one zone.
assertRegions('gold body with snake scales on the hood', [['body'], ['hood']]);
assertRegions('matte black on the roof only with a fine hex texture', [['roof']]);
assertRegions('matte black with a fine hex texture on the roof only', [['roof']]);

// Directional side aliases remain singular; “both sides” remains an explicit two-part target.
const leftOnly = 'On the left side only, pink ghost camo under fine snake-skin texture.';
assert.equal(A.targetOf(leftOnly).id, 'left side');
{
  const plan = A.stackPlan(leftOnly, H.ENV, { alts: 0 });
  assert.ok(plan && plan.lparts, 'left-side stack plan exists');
  assert.deepEqual(Array.from(plan.lparts.parts), ['left side']);
  const reply = A.answer(A.classify(leftOnly, null), H.ENV);
  assert.ok(reply && reply.kind === 'stack');
  assert.deepEqual(targetParts(reply.kits[0].items[0].target.region.part), ['left side']);
  for (const item of reply.kits[0].items) {
    const applied = A.applyPlan(item.card, item.target, H.ENV).steps || [];
    for (const step of applied) if (step.tool === 'add_zone') assert.deepEqual(targetParts(step.args.region.part), ['left side']);
  }
  const tool = A.suggestTool({ ask: leftOnly }, H.ENV);
  assert.deepEqual(targetParts(tool.apply.find(s => s.tool === 'add_zone').args.region.part), ['left side']);
}
for (const ask of [
  'On both sides only, pink ghost camo under fine snake-skin texture.',
  'Pink ghost camo under fine snake-skin texture on both sides only.',
  'Pink ghost camo under fine snake-skin texture on both sides.'
]) {
  assert.equal(A.targetOf(ask).id, 'sides', `${ask}: both sides target alias`);
  const plan = A.stackPlan(ask, H.ENV, { alts: 0 });
  assert.ok(plan && plan.lparts, `${ask}: stack plan exists`);
  assert.deepEqual(Array.from(plan.lparts.parts), ['left side', 'right side']);
  assert.equal(plan.lparts.wholeBody, false, `${ask}: implicit base stays on both sides`);
  const reply = A.answer(A.classify(ask, null), H.ENV);
  assert.ok(reply && reply.kind === 'stack', `${ask}: visible stack answer exists`);
  assert.deepEqual(targetParts(reply.kits[0].items[0].target.region.part), ['left side', 'right side']);
  const tool = A.suggestTool({ ask }, H.ENV);
  assert.deepEqual(targetParts(tool.apply.find(s => s.tool === 'add_zone').args.region.part), ['left side', 'right side']);
}
assertRegions('matte black on the left side only with a fine hex texture', [['left side']]);
assertRegions('fine hex texture on the left side only with matte black', [['left side']]);
assertRegions('matte black on both sides only with a fine hex texture', [['left side', 'right side']]);
assertRegions('fine hex texture on both sides only with matte black', [['left side', 'right side']]);
assertRegions('matte black with a fine hex texture on both sides', [['left side', 'right side']]);

// Recommendation replies remain scoped recommendations, independent of actionable composition plans.
for (const ask of [
  'Give the roof a matte gold carbon look, exclusively on that panel.',
  'Finish everything on the roof in pearl gold, and leave the rest unchanged.'
]) {
  const item = A.classify(ask, null);
  const reply = item && A.answer(item, H.ENV);
  assert.ok(reply && reply.kind === 'recommend', `${ask}: recommendation remains in the recommendation lane`);
  assert.equal(reply.target.id, 'roof');
}

console.log('PASS ai_request_composition_contract.cjs (6 exclusive scopes, 3 body+part compositions, 3 preserved guards, 2 scoped recommendations, 1 singular-side target, 3 both-sides advisor targets, 5 designer side targets)');
