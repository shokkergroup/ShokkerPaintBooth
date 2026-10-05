const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const H = require('../_easy_claude_work/stack_h.js');

const root = H.ROOT;
const oraclePath = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_W7_NAMED_PART_ORACLE_2026-10-03.json');
const oracleHash = 'DD7B2DC88B341E22480B033ED848AEBFF8332255A070945BE98D6384EBF2609C';
assert.equal(crypto.createHash('sha256').update(fs.readFileSync(oraclePath)).digest('hex').toUpperCase(), oracleHash, 'frozen W7 oracle changed');
const oracle = JSON.parse(fs.readFileSync(oraclePath, 'utf8'));
const w = H.load();
for (const file of ['js/spb-pro-design.js', 'js/spb-pro-edit.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), w, { filename: file });
}
const E = w.SpbProEdit;
const env = {
  palette: [
    { hex: '#141416', share_pct: 52 }, { hex: '#f2c500', share_pct: 22 },
    { hex: '#f1f1ee', share_pct: 14 }, { hex: '#1347a8', share_pct: 5 }
  ],
  layers: []
};
function partOf(region) {
  if (!region || region.everything || region.paintable || region.colors || region.layers) return null;
  return region.part || null;
}
function parts(value) { return Array.isArray(value) ? Array.from(value) : [value]; }

let positiveCount = 0;
for (const item of oracle.cases.filter(x => x.expected === 'part-plan')) {
  const plan = E.plan(item.text, env);
  assert.ok(plan && plan.kind === 'ops', `${item.id}: simple named-part command was not claimed: ${JSON.stringify(plan)}`);
  assert.equal(plan.exactPart, true, `${item.id}: exactPart ownership marker missing`);
  assert.equal(plan.ops.length, 1, `${item.id}: extra plan ops: ${JSON.stringify(plan.ops)}`);
  assert.equal(plan.ops[0].target.kind, 'part', `${item.id}: target kind was not a named part`);
  assert.ok(item.regions.includes(`part:${plan.ops[0].target.part}`), `${item.id}: planned wrong part ${plan.ops[0].target.part}`);
  assert.equal(plan.unknown.length, 0, `${item.id}: silently claimed unknown action ${plan.unknown.join(',')}`);
  const compiled = E.compile(plan, env);
  assert.equal(compiled.ask, null, `${item.id}: supported single part operation unexpectedly asks: ${compiled.ask && compiled.ask.text}`);
  assert.equal(compiled.zones.length, 1, `${item.id}: expected one compiled zone, got ${compiled.zones.length}`);
  const zone = compiled.zones[0];
  assert.deepEqual(parts(partOf(zone.region)), item.regions.map(x => x.slice('part:'.length)), `${item.id}: compiled region widened or changed`);
  assert.ok(Array.isArray(zone._meta.parts) && zone._meta.parts.includes(plan.ops[0].target.part), `${item.id}: target-part metadata was lost`);
  if (item.colour) assert.ok(zone.color && zone.color !== 'source', `${item.id}: explicit destination colour was lost`);
  if (item.finish) assert.equal(zone.finish, E.lookById(item.finish).found, `${item.id}: finish metadata was lost`);
  positiveCount++;
}

let negativeCount = 0;
for (const item of oracle.cases.filter(x => x.expected === 'not-part-plan')) {
  const plan = E.plan(item.text, env);
  assert.notEqual(plan && plan.exactPart, true, `${item.id}: advice, layered, unknown, or whole-body text was incorrectly claimed as exactPart`);
  negativeCount++;
}

// Unknown extra actions and clearcoat/material adjustment requests must not be relabelled as a simple new finish.
for (const text of [
  'Make the roof green and add flame graphics.',
  'Everything is too shiny; lower clearcoat on the roof only.',
  'Give the roof a green base with carbon weave on top.'
]) {
  const plan = E.plan(text, env);
  assert.notEqual(plan && plan.exactPart, true, `${text}: exactPart must not swallow an extra or material-channel action`);
}

// Whole-body preservation still asks; explicit positive assignments remain atomic body-plus-part jobs.
{
  const ask = E.plan('Recoat the whole car in matte burgundy; do not change the roof.', env);
  assert.equal(ask.kind, 'ask'); assert.deepEqual(Array.from(ask.protected_parts), ['roof']);
  assert.notEqual(ask.exactPart, true);
}
for (const [text, expected] of [
  ['Paint the entire body green except make the hood gold.', [['body'], ['hood']]],
  ['Repaint the entire vehicle silver, except apply black carbon to the roof.', [['body'], ['roof']]]
]) {
  const plan = E.plan(text, env);
  assert.ok(plan && plan.kind === 'ops', `${text}: explicit assignment plan missing`);
  assert.equal(plan.exactPart, undefined, `${text}: multi-scope plan must not claim exactPart`);
  assert.equal(plan.atomicScope, true, `${text}: positive exception must remain atomic`);
  const compiled = E.compile(plan, env);
  if (plan.unknown.length) {
    assert.ok(compiled.ask && /carbon|roof/i.test(compiled.ask.text), `${text}: unresolved material should request clarification`);
    assert.equal(compiled.zones.length, 0, `${text}: unresolved panel material must not leave a partial body zone`);
    continue;
  }
  assert.equal(compiled.ask, null, `${text}: local supported composition asked: ${compiled.ask && compiled.ask.text}`);
  assert.deepEqual(Array.from(compiled.zones).map(z => z.region.everything ? ['body'] : parts(z.region.part)), expected, `${text}: body/part masks changed`);
}

console.log(`PASS ai_named_part_commands_contract.cjs (${positiveCount} simple part plans, ${negativeCount} non-claims, 3 unknown/material guards, 3 preservation/composition guards)`);
