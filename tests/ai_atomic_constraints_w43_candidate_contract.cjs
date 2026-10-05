/* W43 positive alias oracle frozen before candidate implementation. */
'use strict';
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.resolve(__dirname, '..');
const CAND = path.join(ROOT, '_easy_claude_work', 'ai14h_w43_candidate');
const CANDIDATE_HASHES = Object.freeze({
  guard: 'BA0AF1F9E217695ED733DDE81C8DEC1A735DD1F052E8C06B3098866D392A551C',
  proAI: 'CBDC3BF8F8A843C8B3B0B0A3E143206F711C919691CA525E1101F3C552386DFC',
  design: '0533393FF5F2170236F60D4ED489C7AE52F98805E12B0764DA67A967F756F2E8',
  edit: '8571FCE490F65C6C0C888F6D632860FCA5A05C63834978A4EB262EF9B30C3B0C'
});
const ORACLE = Object.freeze([
  { id: 'W43-P01', text: 'Make the hood chrome and leave its current navy paint alone.', expected: 'one hood-only chrome operation; keep paint color' },
  { id: 'W43-P02', text: 'Make only the roof chrome and keep its existing red paint unchanged.', expected: 'one roof-only chrome operation; keep paint color' },
  { id: 'W43-P03', text: 'Make the hood satin; leave its existing paint alone.', expected: 'one hood-only satin operation; keep paint color' },
  { id: 'W43-P04', text: 'Set the roof gloss while preserving its current blue paint.', expected: 'one roof-only gloss operation; keep paint color' },
  { id: 'W43-P05', text: 'Give only the hood a brushed-aluminum finish; do not recolor it.', expected: 'one hood-only brushed operation; keep paint color' },
  { id: 'W43-P06', text: 'Turn the roof chrome and leave the roof red and its region alone.', expected: 'one roof-only chrome operation; preserve paint and region' },
  { id: 'W43-P07', text: 'Make only the hood satin, keep the current black color, and leave its mask unchanged.', expected: 'one hood-only satin operation; preserve paint and mask' },
  { id: 'W43-P08', text: 'Set the roof to gloss, keeping the existing red paint and region mask intact.', expected: 'one roof-only gloss operation; preserve paint and mask' },
  { id: 'W43-P09', text: 'Make the hood chrome but leave its current navy paint alone.', expected: 'one hood-only chrome operation; keep paint color across but-clause' },
  { id: 'W43-P10', text: 'Keep all sponsor decals unchanged, then make only the roof deep red.', expected: 'one roof-red operation; do not interpret the preservation note as a finish lookup' }
]);
const ORACLE_SHA256 = 'ED23B8C60E0E6F180528F4A388B14694D9B9033698DBE076FA357860B7DED060';
const actualOracleHash = crypto.createHash('sha256').update(JSON.stringify(ORACLE) + '\n').digest('hex').toUpperCase();
if (ORACLE_SHA256 !== 'PENDING' && actualOracleHash !== ORACLE_SHA256) throw new Error('W43 positive alias oracle changed: ' + actualOracleHash);

if (process.argv.includes('--freeze-only')) {
  console.log(JSON.stringify({ sha256: actualOracleHash, cases: ORACLE.length, oracle: ORACLE }, null, 2)); process.exit(0);
}

async function main() {
  const fileMap = { guard: 'spb-ai-complete-instruction-guard.js', proAI: 'spb-pro-ai.js', design: 'spb-pro-design.js', edit: 'spb-pro-edit.js' };
  for (const [key, file] of Object.entries(fileMap)) {
    const got = crypto.createHash('sha256').update(fs.readFileSync(path.join(CAND, 'js', file))).digest('hex').toUpperCase();
    assert.equal(got, CANDIDATE_HASHES[key], 'frozen W43 candidate changed: ' + key);
  }
  const H = require('../_easy_claude_work/stack_h.js');
  const w = H.load();
  for (const file of ['spb-pro-design.js', 'spb-pro-edit.js', 'spb-ai-complete-instruction-guard.js']) {
    vm.runInContext(fs.readFileSync(path.join(CAND, 'js', file), 'utf8'), w, { filename: 'W43 candidate ' + file });
  }
  const env = { palette: [
    { hex: '#c8102e', share_pct: 60 }, { hex: '#141416', share_pct: 20 },
    { hex: '#1347a8', share_pct: 10 }, { hex: '#f2c500', share_pct: 5 }
  ], layers: [] };
  const outcomes = [], failures = [];
  for (const c of ORACLE) {
    const plan = w.SpbProEdit.plan(c.text, env);
    const compiled = plan && plan.kind === 'ops' ? w.SpbProEdit.compile(plan, env) : null;
    const row = { id: c.id, text: c.text, plan: plan && { kind: plan.kind, exactPart: plan.exactPart, ops: plan.ops && plan.ops.map(op => ({ target: op.target, look: op.look && op.look.id, colour: op.colour, ext: op.ext })), unknown: plan.unknown }, compiled: compiled && { ask: compiled.ask, zones: compiled.zones.map(z => ({ part: z.region && z.region.part, color: z.color, finish: z.finish, pattern: z.pattern || null })) } };
    if (c.id === 'W43-P10') {
      const op = plan && plan.kind === 'ops' && plan.ops.length === 1 && plan.ops[0];
      if (!op || !plan.exactPart || op.target.kind !== 'part' || op.target.part !== 'roof' || !op.colour || op.look || op.ext || plan.unknown.length) failures.push({ id: c.id, issue: 'preservation note still became an operation, finish lookup or unknown clause', plan });
      if (!compiled || compiled.ask || compiled.zones.length !== 1 || compiled.zones[0].region.part !== 'roof' || !/^#/.test(compiled.zones[0].color) || compiled.zones[0].pattern) failures.push({ id: c.id, issue: 'note did not compile to one roof-color zone', compiled });
      outcomes.push({ id: c.id, planKind: plan && plan.kind, exactPart: plan && plan.exactPart, ops: plan && plan.ops && plan.ops.map(op => ({ part: op.target && op.target.part, finish: op.look && op.look.id, color: op.colour && op.colour.name, ext: op.ext })), unknown: plan && plan.unknown, compiledZones: compiled && compiled.zones.map(z => ({ part: z.region && z.region.part, finish: z.finish, color: z.color, pattern: z.pattern || null })) });
      continue;
    }
    if (!plan || plan.kind !== 'ops' || plan.exactPart !== true || plan.ops.length !== 1) failures.push({ id: c.id, issue: 'not one exact-part operation', plan });
    else {
      const op = plan.ops[0];
      const expectedPart = ['W43-P02', 'W43-P04', 'W43-P06', 'W43-P08'].includes(c.id) ? 'roof' : 'hood';
      if (!op.target || op.target.kind !== 'part' || op.target.part !== expectedPart) failures.push({ id: c.id, issue: 'wrong target part', op });
      if (!op.look || op.colour !== null || (plan.unknown && plan.unknown.length)) failures.push({ id: c.id, issue: 'finish/color/unknown boundary wrong', plan });
      if (!compiled || compiled.ask || compiled.zones.length !== 1 || compiled.zones[0].region.part !== op.target.part || compiled.zones[0].color !== 'source' || compiled.zones[0].pattern || compiled.zones[0].spec_patterns) failures.push({ id: c.id, issue: 'compile not one source-color finish-only zone', compiled });
    }
    outcomes.push({ id: c.id, planKind: plan && plan.kind, exactPart: plan && plan.exactPart, ops: plan && plan.ops && plan.ops.map(op => ({ part: op.target && op.target.part, finish: op.look && op.look.id, color: op.colour })), unknown: plan && plan.unknown, compiledZones: compiled && compiled.zones.map(z => ({ part: z.region && z.region.part, finish: z.finish, color: z.color, pattern: z.pattern || null })) });
  }
  console.log(JSON.stringify({ status: failures.length ? 'BLOCKED' : 'PASS', oracleSha256: actualOracleHash, cases: ORACLE.length, candidateHashes: CANDIDATE_HASHES, outcomes, failures }, null, 2));
  if (failures.length) process.exitCode = 1;
}
main().catch(e => { console.error(e.stack || e); process.exitCode = 1; });
