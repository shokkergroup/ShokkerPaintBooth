const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const H = require('../_easy_claude_work/stack_h.js');

const w = H.load();
const A = w.SpbProAdvisor;
const AT = w.SpbAIAtlas;
const C = w.SpbAICards;
vm.runInContext(fs.readFileSync(path.join(H.ROOT, 'js/spb-pro-design.js'), 'utf8'), w, { filename: 'js/spb-pro-design.js' });
const D = w.SpbProDesign;

function apply(ask) {
  const result = A.suggestTool({ ask }, H.ENV);
  assert.ok(result && result.stack && result.stack.length, `advisor stack missing for: ${ask}`);
  result.stack.forEach(layer => {
    assert.ok(AT.lookup(layer.key), `unknown atlas id ${layer.key} for: ${ask}`);
    assert.ok(C.card(layer.key), `unknown card id ${layer.key} for: ${ask}`);
  });
  return result.apply || [];
}
function answer(ask) {
  const item = A.classify(ask, null);
  const result = item && A.answer(item, H.ENV);
  assert.ok(result && result.kind === 'stack' && result.kits && result.kits.length, `visible stack answer missing for: ${ask}`);
  const firstLine = String(result.text || '').split('\n')[0];
  assert.ok(!/body\s*\+/.test(firstLine), `answer copy must keep the named-only scope: ${firstLine}`);
  return result;
}
function addedPart(steps, part) {
  return steps.filter(step => step.tool === 'add_zone' && step.args.region &&
    (Array.isArray(step.args.region.part) ? step.args.region.part.includes(part) : step.args.region.part === part));
}

// A material explicitly restricted to a part carries its texture in the same part zone.
{
  const ask = 'matte black on the roof only with a fine hex texture';
  const steps = apply(ask);
  assert.equal(steps.some(step => step.tool === 'edit_zone'), false, 'part-only roof stack must not edit body zones');
  assert.equal(steps.length, 1, 'roof base and texture should be one zone');
  assert.equal(addedPart(steps, 'roof').length, 1);
  assert.equal(steps[0].args.finish, 'base::matte');
  assert.ok((steps[0].args.spec_patterns || []).some(layer => layer.id === 'spov2_stitched_hex'));
}

// Reversed order and placement exclusivity keep both the Use plan and visible answer on the roof.
for (const [ask, parts] of [
  ['Put a fine carbon pattern on the roof only, in deep blue.', ['roof']],
  ['Only the roof gets a pearl gold base and little hex cells.', ['roof']],
  ['matte black with a fine hex texture on the roof only', ['roof']],
  ['matte black with fine hex texture just on roof', ['roof']],
  ['matte black exclusively on the roof with fine hex', ['roof']],
  ['hex pattern on just the sides, white base', ['left side', 'right side']]
]) {
  if (ask.startsWith('Put a fine carbon') || ask.startsWith('Only the roof')) {
    const result = answer(ask);
    assert.match(result.text.split('\n')[0], /on the roof:/);
    for (const item of result.kits[0].items) {
      assert.equal(item.target.region.part, 'roof', `${ask}: card target`);
      const applied = A.applyPlan(item.card, item.target, H.ENV).steps || [];
      assert.equal(applied.some(step => step.tool === 'edit_zone'), false, `${ask}: no body-zone edit`);
      for (const step of applied) if (step.tool === 'add_zone') assert.equal(step.args.region.part, 'roof', `${ask}: scoped zone`);
    }
  }
  const steps = apply(ask);
  assert.equal(steps.some(step => step.tool === 'edit_zone'), false, `${ask}: suggested apply must not mutate body zones`);
  assert.equal(steps.length, 1, `${ask}: combined part zone`);
  const actualParts = Array.isArray(steps[0].args.region.part) ? Array.from(steps[0].args.region.part) : [steps[0].args.region.part];
  assert.deepEqual(actualParts, parts, `${ask}: scoped region`);
}

// All named parts in a part-only base scope receive the same combined stack.
{
  const steps = apply('matte black on the roof and hood only with a fine hex texture');
  assert.equal(steps.some(step => step.tool === 'edit_zone'), false, 'multi-part-only stack must not edit body zones');
  assert.equal(steps.length, 1);
  assert.deepEqual(Array.from(steps[0].args.region.part), ['hood', 'roof']);
  assert.equal(steps[0].args.finish, 'base::matte');
  assert.ok((steps[0].args.spec_patterns || []).some(layer => layer.id === 'spov2_stitched_hex'));
}

// A colour stated only for the hood stays on the hood with its snake pattern.
{
  const steps = apply('snake scales on the hood only in gold');
  assert.equal(steps.some(step => step.tool === 'edit_zone'), false);
  assert.equal(steps.length, 1);
  assert.equal(addedPart(steps, 'hood').length, 1);
  assert.equal(steps[0].args.color, 'finish');
  assert.equal(steps[0].args.finish, 'monolithic::cx_gold_green');
  assert.equal((steps[0].args.pattern || {}).id, 'snake_skin');
}

// Explicit whole-body wording still changes body zones and adds the requested hood layer.
for (const ask of ['gold body with snake scales on the hood only', 'gold all over with snake scales on hood']) {
  const steps = apply(ask);
  const summary = A.suggestTool({ ask }, H.ENV);
  assert.match(summary.part, /body.*hood/, `${ask}: tool summary includes both scopes`);
  assert.doesNotMatch(summary.note, /ONE zone|one zone, every layer/, `${ask}: tool summary permits multiple zones`);
  const answer = A.answer(A.classify(ask, null), ask, H.ENV);
  assert.ok(answer.kits && answer.kits.length);
  assert.doesNotMatch(answer.kits[0].blurb, /one zone/i, `${ask}: kit blurb permits body and part zones`);
  const edits = steps.filter(step => step.tool === 'edit_zone');
  assert.deepEqual(Array.from(edits, step => step.args.zone_id).sort(), ['z5', 'z6'], `${ask}: body zones`);
  const hood = addedPart(steps, 'hood');
  assert.equal(hood.length, 1, `${ask}: hood layer`);
  assert.ok((hood[0].args.pattern || {}).id === 'snake_skin');
}

// Ordinary whole-car stacks without named parts retain their whole-car target.
{
  const steps = apply('matte black with a fine hex texture');
  assert.deepEqual(Array.from(steps.filter(step => step.tool === 'edit_zone'), step => step.args.zone_id).sort(), ['z5', 'z6']);
  assert.equal(steps.some(step => step.tool === 'add_zone' && step.args.region && step.args.region.part), false);
  assert.ok(steps.some(step => (step.args.spec_patterns || []).some(layer => layer.id === 'spov2_stitched_hex')));
}

// A named part without an exclusivity word keeps the ordinary body-base + part-layer behavior.
{
  const steps = apply('matte black with a fine hex texture on the roof');
  assert.deepEqual(Array.from(steps.filter(step => step.tool === 'edit_zone'), step => step.args.zone_id).sort(), ['z5', 'z6']);
  assert.equal(addedPart(steps, 'roof').length, 1);
  assert.ok((addedPart(steps, 'roof')[0].args.spec_patterns || []).some(layer => layer.id === 'spov2_stitched_hex'));
}

// The true designer compound path must keep the part-only stack scoped, while explicit body+part stays split.
{
  const scoped = D.compoundPlan('matte black on the roof only with a fine hex texture');
  assert.ok(scoped && scoped.zones.length === 1);
  assert.equal(JSON.stringify(scoped.zones[0].region), JSON.stringify({ part: 'roof' }));
  assert.equal(scoped.zones[0].finish, 'base::matte');
  assert.equal(scoped.zones[0].pattern.id, 'hex_carbon');

  const reversed = D.compoundPlan('matte black with a fine hex texture on the roof only');
  assert.ok(reversed && reversed.zones.length === 1);
  assert.equal(JSON.stringify(reversed.zones[0].region), JSON.stringify({ part: 'roof' }));
  assert.equal(reversed.zones[0].finish, 'base::matte');
  assert.equal(reversed.zones[0].pattern.id, 'hex_carbon');

  const whole = D.compoundPlan('gold body with snake scales on the hood only');
  assert.ok(whole && whole.zones.some(zone => zone.region.everything));
  assert.ok(whole.zones.some(zone => zone.region.part === 'hood' && zone.spec_patterns.some(layer => layer.id === 'spec_snake_scales')));
}

console.log('PASS ai_stack_scope_contract.cjs');
