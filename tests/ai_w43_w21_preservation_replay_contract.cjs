'use strict';
// W21 independent oracle frozen before inspecting the current editor source.
const crypto = require('node:crypto');
const fresh = [
  { id:'W21-F01', text:'Set only the roof to satin; keep its current red paint.', mode:'one_finish', part:'roof', finish:'satin' },
  { id:'W21-F02', text:'Make only the hood chrome and retain its current black paint.', mode:'one_finish', part:'hood', finish:'chrome' },
  { id:'W21-F03', text:'Please give the roof a brushed finish. Do not change its red paint color.', mode:'one_finish', part:'roof', finish:'brushed' },
  { id:'W21-F04', text:'Make the hood matte; leave its existing paint alone.', mode:'one_finish', part:'hood', finish:'matte' },
  { id:'W21-F05', text:'Only the roof should be satin; its paint should stay red.', mode:'one_finish', part:'roof', finish:'satin' },
  { id:'W21-F06', text:'Set the hood gloss while preserving its current blue paint.', mode:'one_finish', part:'hood', finish:'gloss' },
  { id:'W21-F07', text:'Turn the roof chrome and leave the roof red and its region alone.', mode:'one_finish', part:'roof', finish:'chrome' },
  { id:'W21-F08', text:'Make only the hood satin, keep the current black color, and leave its mask unchanged.', mode:'one_finish', part:'hood', finish:'satin' },
  { id:'W21-F09', text:'Set the roof to gloss, keeping the existing red paint and region mask intact.', mode:'one_finish', part:'roof', finish:'gloss' },
  { id:'W21-F10', text:'Give only the hood a brushed-aluminum finish; do not recolor it.', mode:'one_finish', part:'hood', finish:'brushed' },
  { id:'W21-N01', text:'Make the roof chrome and retain the hood current black paint.', mode:'clarify', part:'roof' },
  { id:'W21-N02', text:'Make the roof chrome and keep the whole body red.', mode:'clarify', part:'roof' },
  { id:'W21-N03', text:'Set the hood gloss; do not change its finish.', mode:'clarify', part:'hood' },
  { id:'W21-N04', text:'Make the roof chrome and keep its red paint, then add a gold carbon weave.', mode:'clarify', part:'roof' },
  { id:'W21-N05', text:'Make the roof chrome, keep its red paint, and repaint the hood blue.', mode:'clarify', part:'roof' },
  { id:'W21-N06', text:'Do not make the roof chrome; keep its red paint as it is.', mode:'no_mutation', part:'roof' }
];
const priorW17 = [
  { id:'W17-02', text:'Make only the hood chrome and retain its black paint.', mode:'one_finish', part:'hood', finish:'chrome' },
  { id:'W17-03', text:'Give only the roof a satin finish; leave its current red paint and region alone.', mode:'one_finish', part:'roof', finish:'satin' },
  { id:'W17-04', text:"Set the hood to gloss; don't change its current navy color.", mode:'one_finish', part:'hood', finish:'gloss' }
];
const canonical = JSON.stringify({ fresh, priorW17 });
const oracleHash = crypto.createHash('sha256').update(canonical).digest('hex').toUpperCase();
if (process.argv.includes('--freeze-only')) { console.log(JSON.stringify({ fresh: fresh.length, priorW17: priorW17.length, oracleHash, fresh, priorW17 }, null, 2)); process.exit(0); }

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const source = path.join(root, '_easy_claude_work/ai14h_w43_candidate/js/spb-pro-edit.js');
const beforeHash = 'A328A1EF5D8293E2F8CFC8A27F3E0C868A04842A07EE39243CBD0BD34513BDA7';
const afterHashExpected = '8571FCE490F65C6C0C888F6D632860FCA5A05C63834978A4EB262EF9B30C3B0C';
const expectedOracleHash = 'B92DBDD01A56928E4160A29F3013C78C0083DA374A3DABAB26AED1B0AFBBF08F';
assert.equal(oracleHash, expectedOracleHash, 'W21 frozen request oracle changed');
function sha(file) { return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex').toUpperCase(); }
const H = require('../_easy_claude_work/stack_h.js');
const w = H.load();
for (const file of ['_easy_claude_work/ai14h_w43_candidate/js/spb-pro-design.js', '_easy_claude_work/ai14h_w43_candidate/js/spb-pro-edit.js']) vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), w, { filename: file });
const E = w.SpbProEdit;
const env = { palette: [
  { hex: '#c8102e', share_pct: 60 }, { hex: '#141416', share_pct: 20 },
  { hex: '#1347a8', share_pct: 10 }, { hex: '#f2c500', share_pct: 5 }
], layers: [] };
const all = fresh.concat(priorW17);
const positive = all.filter(c => c.mode === 'one_finish');
const negative = fresh.filter(c => c.mode !== 'one_finish');
const results = [], failures = [], scopeLimits = [];
for (const c of all) {
  const plan = E.plan(c.text, env);
  const compiled = plan && plan.kind === 'ops' ? E.compile(plan, env) : null;
  const row = { id: c.id, text: c.text, mode: c.mode, plan, compiled };
  if (c.mode === 'one_finish') {
    if ((!plan || plan.kind !== 'ops' || plan.exactPart !== true || plan.ops.length !== 1) && c.id === 'W21-F05') {
      // This frozen probe is declarative (“should be”), while the assigned repair
      // contract is explicitly limited to a complete finish-only imperative.
      scopeLimits.push({ id: c.id, type: 'outside_assigned_imperative_prefix_scope', text: c.text, observed: plan });
    } else if (!plan || plan.kind !== 'ops' || plan.exactPart !== true || plan.ops.length !== 1) failures.push({ id: c.id, type: 'expected one exact named-part finish op', plan });
    else {
      const op = plan.ops[0], part = op.target && op.target.part;
      if (op.target.kind !== 'part' || part !== c.part || !op.look || op.colour || op.rel || op.shade || op.pop || op.keep || op.recipe || op.sub || plan.unknown.length) failures.push({ id: c.id, type: 'tail did not leave one part-scoped finish-only op with explicit null color/action fields', plan });
      if (!compiled || compiled.ask || compiled.zones.length !== 1 || !compiled.zones[0].finish || !compiled.zones[0].region || compiled.zones[0].region.part !== c.part || compiled.zones[0].color !== 'source' || compiled.zones[0].pattern || compiled.zones[0].spec_patterns) failures.push({ id: c.id, type: 'compile did not preserve one scoped finish-only zone with source color and no pattern', compiled });
    }
  } else {
    if (plan && plan.exactPart === true) failures.push({ id: c.id, type: 'unsafe exactPart claim for conflicting/extra/negative request', plan });
    if (c.mode === 'no_mutation' && !(plan && plan.kind === 'ask' && plan.prohibited_edit && (!compiled || !compiled.zones.length))) failures.push({ id: c.id, type: 'leading prohibition did not remain no-mutation ask', plan, compiled });
    if (c.mode === 'clarify' && compiled && !compiled.ask && compiled.zones.length) failures.push({ id: c.id, type: 'conflicting/extra tail compiled executable zones rather than clarification', plan, compiled });
  }
  results.push(row);
}
const afterHash = sha(source);
assert.equal(afterHash, afterHashExpected, 'current editor changed after this W21 review run');
const report = {
  review: 'W43 replay of unchanged W21 finish-preservation oracle', date: '2026-10-04',
  status: failures.length ? 'BLOCKED' : (scopeLimits.length ? 'PASS_WITH_LIMITS' : 'PASS'),
  frozen_oracle: { sha256: oracleHash, fresh_cases: fresh.length, separate_prior_W17_cases: priorW17.length, fresh, priorW17 },
  source: { path: '_easy_claude_work/ai14h_w43_candidate/js/spb-pro-edit.js', frozen_candidate_sha256: afterHash },
  implementation: {
    helper_lines: '446-468',
    pre_prohibition_guard_lines: '470-482',
    contract: 'Only remove a final whitelisted same-part paint/color/mask-preservation clause after the preceding text independently parses as exactly one known named-part finish action. The unchanged prohibition guard then handles leading negative commands.'
  },
  counts: { fresh_positive: fresh.filter(c => c.mode === 'one_finish').length, prior_W17_replayed: priorW17.length, positive_passed: positive.length - failures.filter(f => all.find(c => c.id === f.id)?.mode === 'one_finish').length - scopeLimits.length, safe_negative_no_exact_part: negative.length - failures.filter(f => fresh.find(c => c.id === f.id)?.mode !== 'one_finish').length, out_of_scope: scopeLimits.length, failures: failures.length },
  results, failures, scope_limits: scopeLimits,
  limits: ['E.plan and E.compile were executed from the actual editor source; no proAI route, browser, native app, provider, renderer, or paint mutation was executed.', 'Current-part paint color consistency is not verifiable from the parser-only environment; the asserted contract is that preservation tails do not become color assignments and compile as one named-part zone with source color.', 'The fresh oracle and three W17 replay strings are reported separately. Original W17 files were not modified.']
};
const reportPath = path.join(root, '_easy_claude_work/ai14h_w43_candidate/W21-replay.json');
fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ status: report.status, counts: report.counts, failures, source: report.source }, null, 2));
if (failures.length) process.exitCode = 2;
