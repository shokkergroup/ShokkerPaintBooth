'use strict';

const path = require('path');
const { spawnSync } = require('child_process');

const root = path.resolve(__dirname, '..'), asJson = process.argv.includes('--json');
const spawnOpts = { cwd: root, encoding: 'utf8', windowsHide: true, timeout: 10 * 60 * 1000, maxBuffer: 32 * 1024 * 1024 };

function preflightStatus() {
  const run = spawnSync(process.execPath, [path.join(root, 'scripts/spb_release_preflight.js'), '--mode=status', '--json'], spawnOpts);
  const detail = String(run.error && run.error.message || run.stderr || run.stdout || 'no JSON output').trim();
  try { return JSON.parse(run.stdout); }
  catch (_) { return { ok: false, checks: [{ name: 'preflight status execution', requiredFor: ['build', 'stage', 'deploy', 'activate'], ok: false, detail: detail.slice(0, 500) }] }; }
}

function readScorecardSummary() {
  const result = spawnSync('python', [path.join(root, 'scripts/spb_scorecard_drift_summary.py'), '--sample', '0'], spawnOpts);
  return result.status === 0 ? result.stdout.trim().split(/\r?\n/).slice(0, 6) : [];
}

const preflight = preflightStatus(), summary = readScorecardSummary();
const gates = (preflight.checks || []).map((row) => ({
  name: row.name, status: row.ok ? 'PASS' : 'BLOCKED', requiredFor: row.requiredFor || [],
  blocker: row.ok ? null : String(row.detail || 'gate failed').split(/\r?\n/).slice(-6).join('\n'),
}));
const phases = Object.fromEntries(['build', 'stage', 'deploy', 'activate'].map((phase) => [phase,
  gates.some((gate) => gate.requiredFor.includes(phase) && gate.status !== 'PASS') ? 'BLOCKED' : 'PASS']));

if (asJson) {
  console.log(JSON.stringify({ schemaVersion: 1, phases, gates, scorecardSummary: summary }, null, 2));
  process.exit(0);
}

console.log('SPB release gate status');
console.log(`phases: ${Object.entries(phases).map(([phase, status]) => `${phase}=${status}`).join('  ')}`);
for (const gate of gates) {
  console.log(`${gate.status.padEnd(7)} ${gate.name}  [${gate.requiredFor.join(', ')}]`);
  if (gate.blocker) for (const line of gate.blocker.split(/\r?\n/)) console.log(`  ${line}`);
}
if (summary.length) {
  console.log('scorecard_summary:');
  for (const line of summary) console.log(`  ${line}`);
}
