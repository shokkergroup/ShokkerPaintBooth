'use strict';

const path = require('path');
const { spawnSync } = require('child_process');

const root = path.resolve(__dirname, '..');
const asJson = process.argv.includes('--json');
const spawnOpts = { cwd: root, encoding: 'utf8' };

function runJson(script) {
  const result = spawnSync(process.execPath, [path.join(root, script), '--json'], spawnOpts);
  if (result.status !== 0) throw new Error(`${script} failed: ${result.stderr || result.stdout}`);
  return JSON.parse(result.stdout);
}

function readScorecardSummary() {
  const result = spawnSync('python', [path.join(root, 'scripts/spb_scorecard_drift_summary.py'), '--sample', '0'], spawnOpts);
  return result.status === 0 ? result.stdout.trim().split(/\r?\n/).slice(0, 6) : [];
}

const budget = runJson('scripts/spb_file_budget.js');
const drift = runJson('scripts/spb_generated_drift_guard.js');
const overCeiling = budget.filter((row) => row.status === 'OVER_CEILING' || row.status === 'MISSING');
const drifted = drift.filter((row) => row.status === 'DRIFTED_UP' || row.status === 'MISSING');
const summary = readScorecardSummary();

if (asJson) {
  console.log(JSON.stringify({
    fileBudget: { status: overCeiling.length ? 'BLOCKED' : 'PASS', blockers: overCeiling },
    generatedDrift: { status: drifted.length ? 'BLOCKED' : 'PASS', blockers: drifted },
    scorecardSummary: summary,
  }, null, 2));
  process.exit(0);
}

console.log('SPB release gate status');
console.log(`file_budget: ${overCeiling.length ? 'BLOCKED' : 'PASS'}`);
for (const row of overCeiling) console.log(`  - ${row.file}: ${row.status} (${row.lines}/${row.ceiling})`);
console.log(`generated_drift: ${drifted.length ? 'BLOCKED' : 'PASS'}`);
for (const row of drifted) console.log(`  - ${row.file}: ${row.status} (${row.lines}/${row.maxLines})`);
if (summary.length) {
  console.log('scorecard_summary:');
  for (const line of summary) console.log(`  ${line}`);
}
