#!/usr/bin/env node
/* Non-mutating, phase-aware release preflight. */
'use strict';

const { spawnSync } = require('child_process');
const path = require('path');

const ROOT = path.resolve(__dirname, '..'), asJson = process.argv.includes('--json');
const modeToken = process.argv.find((arg) => arg.startsWith('--mode='));
const mode = modeToken ? modeToken.slice(7) : 'activate';
const manifestToken = process.argv.find((arg) => arg.startsWith('--manifest='));
const allPhases = ['build', 'stage', 'deploy', 'activate'];
const common = [
  ['version identity', process.execPath, ['scripts/spb_current_state.js', '--check-version']],
  ['context target integrity', process.execPath, ['scripts/spb_context_target_lint.js']],
  ['Layer suite manifest', process.execPath, ['scripts/spb_layer_regression.js', '--verify-plan']],
  ['Easy suite manifest', process.execPath, ['scripts/spb_easy_regression.js', '--verify-plan']],
  ['Easy featured quality/uniqueness', process.execPath, ['scripts/spb_easy_featured_audit.js']],
  ['canonical release fixture', 'python', ['scripts/spb_release_fixture_audit.py']],
  ['runtime mirror sync', process.execPath, ['scripts/sync-runtime-copies.js', '--check']],
  ['file-budget gate', process.execPath, ['scripts/spb_file_budget.js', '--enforce']],
  ['generated-drift gate', process.execPath, ['scripts/spb_generated_drift_guard.js', '--enforce']],
].map(([name, exe, args]) => ({ name, exe, args, requiredFor: allPhases }));
const evidenceCheck = (name, evidenceMode, requiredFor) => ({ name, exe: process.execPath,
  args: ['scripts/spb_release_evidence_gate.js', `--mode=${evidenceMode}`, ...(manifestToken ? [manifestToken] : [])], requiredFor });
let checks = common;
if (mode === 'prebuild') checks = [...common, evidenceCheck('source/prebuild candidate evidence', 'prebuild', ['build'])];
else if (mode === 'prestage') checks = [...common, evidenceCheck('prestage built-artifact evidence', 'prestage', ['stage', 'deploy'])];
else if (mode === 'activate') checks = [...common, evidenceCheck('activation full packaged evidence', 'activate', ['deploy', 'activate'])];
else if (mode === 'status') checks = [...common,
  evidenceCheck('source/prebuild candidate evidence', 'prebuild', ['build']),
  evidenceCheck('prestage built-artifact evidence', 'prestage', ['stage', 'deploy']),
  evidenceCheck('activation full packaged evidence', 'activate', ['deploy', 'activate'])];
else checks = [{ name: `valid preflight mode (${mode})`, exe: null, args: [], requiredFor: allPhases }];

const results = checks.map((check) => {
  if (!check.exe) return { name: check.name, requiredFor: check.requiredFor, ok: false, exitCode: null, detail: 'mode must be prebuild, prestage, activate, or status' };
  const run = spawnSync(check.exe, check.args, { cwd: ROOT, encoding: 'utf8', windowsHide: true, timeout: 10 * 60 * 1000, maxBuffer: 32 * 1024 * 1024 });
  const output = `${run.stdout || ''}${run.stderr || ''}${run.error ? `\n${run.error.message}` : ''}`.trim();
  return { name: check.name, requiredFor: check.requiredFor, ok: run.status === 0, exitCode: run.status, detail: output.split(/\r?\n/).slice(-30).join('\n') };
});
const result = { schemaVersion: 1, mode, ok: results.every((row) => row.ok), checks: results };
if (asJson) process.stdout.write(JSON.stringify(result, null, 2) + '\n');
else {
  for (const row of results) {
    console[row.ok ? 'log' : 'error'](`${row.ok ? 'PASS' : 'FAIL'}  ${row.name}  [${row.requiredFor.join(', ')}]`);
    if (!row.ok && row.detail) console.error(row.detail);
  }
  console[result.ok ? 'log' : 'error'](`\nRelease ${mode} preflight ${result.ok ? 'passed' : 'blocked'}.`);
}
process.exit(result.ok ? 0 : 1);
