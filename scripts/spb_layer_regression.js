#!/usr/bin/env node
/**
 * spb_layer_regression.js - the standing LAYER PANEL regression sweep
 * (built by the 2026-08-21 layer gauntlet; every check maps to a shipped fix:
 * A escapeHtml/alpha-lock/hidden-restriction/merge-crop, B search/delete-key/
 * knockout/export/merge-vis/zone-badges/clip-indent/badges, C autosave/thumbs/
 * cycling/PS-roundtrip/dropped-report/undo-guard, D multi-select/groups/
 * gesture-cache).
 *
 *   node scripts/spb_layer_regression.js --url http://127.0.0.1:PORT/paint-booth-v2.html [--out DIR]
 *
 * Exit 0 = all green. The target URL is mandatory so a release run cannot
 * silently attach to a stale developer server on :59876.
 */
const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

const HERE = __dirname;
const PLAN = path.join(HERE, 'shotplans', 'layer-panel-regression.json');
const outIdx = process.argv.indexOf('--out');
const OUT = outIdx > -1 ? process.argv[outIdx + 1]
    : path.join(HERE, '..', '_layer_gauntlet', 'shots', 'regression');
const EXPECTED_SHOTS = [
    'A-block-verify', 'B-block-verify', 'C-mini-verify', 'C-block2-verify',
    'D1-verify', 'D2-verify', 'D3-verify', 'offcanvas-commit-verify',
    'contract-sweep', 'stackclaim-verify',
];
const EXPECTED_CHECKS = 95;
const EXPECTED_PLAN_SHA256 = '7d6614dd8b6898d1533e849129986a188e79ccc02b049b33f43c7645714893ae';
const planSha256 = crypto.createHash('sha256').update(fs.readFileSync(PLAN)).digest('hex');
if (planSha256 !== EXPECTED_PLAN_SHA256) {
    console.error('FAIL  layer plan bytes changed without updating the pinned manifest hash');
    console.error('expected: ' + EXPECTED_PLAN_SHA256);
    console.error('actual  : ' + planSha256);
    process.exit(1);
}
const planShotNames = JSON.parse(fs.readFileSync(PLAN, 'utf8')).map((shot) => shot.name);
if (JSON.stringify(planShotNames) !== JSON.stringify(EXPECTED_SHOTS)) {
    console.error('FAIL  layer plan manifest changed without updating the pinned contract');
    console.error('expected: ' + EXPECTED_SHOTS.join(', '));
    console.error('actual  : ' + planShotNames.join(', '));
    process.exit(1);
}
if (process.argv.includes('--verify-plan')) {
    console.log(`LAYER PLAN MANIFEST: ${EXPECTED_SHOTS.length} shots, ${EXPECTED_CHECKS} runtime checks pinned`);
    process.exit(0);
}
const urlIdx = process.argv.indexOf('--url');
if (urlIdx < 0 || !process.argv[urlIdx + 1]) {
    console.error('FAIL  --url is required. Start an isolated SPB backend and pass its exact paint-booth URL.');
    console.error('      The standing runner will not default to the live/developer :59876 instance.');
    process.exit(2);
}
const shotArgs = [path.join(HERE, 'spb_shot.js'), '--plan', PLAN, '--out', OUT];
shotArgs.push('--url', process.argv[urlIdx + 1]);

const runStartedAt = Date.now();
const res = spawnSync(process.execPath, shotArgs,
    { encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 });
const stdout = (res.stdout || '') + (res.stderr || '');
const line = stdout.split('\n').find((l) => l.indexOf('JS [') === 0);
if (!line) {
    console.error(stdout.trim().split('\n').slice(-8).join('\n'));
    console.error('\nFAIL  the sweep produced no results (is the server on :59876?)');
    process.exit(1);
}
let pass = 0, fail = 0, broken = 0;
const failures = [];
const shots = JSON.parse(line.slice(3));
const actualShotNames = shots.map((shot) => shot.name);
if (JSON.stringify(actualShotNames) !== JSON.stringify(EXPECTED_SHOTS)) {
    broken++;
    failures.push(`suite manifest mismatch: expected ${EXPECTED_SHOTS.join(', ')}; got ${actualShotNames.join(', ')}`);
}
for (const shotName of EXPECTED_SHOTS) {
    const evidencePath = path.join(OUT, shotName + '.png');
    let stat = null;
    try { stat = fs.statSync(evidencePath); } catch (_) {}
    if (!stat || stat.size < 1024 || stat.mtimeMs + 1000 < runStartedAt) {
        broken++;
        failures.push('missing/stale screenshot evidence: ' + shotName);
    }
}
const checkIds = new Set();
for (const shot of shots) {
    console.log('\n' + shot.name);
    if (shot.shotError || shot.jsThrew || shot.jsError) {
        broken++;
        console.log('  BROKEN  ' + (shot.shotError || shot.jsThrew || shot.jsError));
        failures.push(shot.name + ' broken');
        continue;
    }
    let checks;
    try { checks = JSON.parse(shot.js); } catch (e) {
        broken++; console.log('  BROKEN  unreadable result'); failures.push(shot.name); continue;
    }
    for (const c of checks) {
        const checkId = shot.name + '::' + c.k;
        if (checkIds.has(checkId)) {
            broken++; failures.push('duplicate check id: ' + checkId); continue;
        }
        checkIds.add(checkId);
        const d = c.detail ? '  [' + c.detail + ']' : '';
        if (c.pass) { pass++; console.log('  PASS  ' + c.k + d); }
        else { fail++; console.log('  FAIL  ' + c.k + d); failures.push(shot.name + ' - ' + c.k + d); }
    }
}
if (pass + fail !== EXPECTED_CHECKS) {
    broken++;
    failures.push(`check-count mismatch: expected ${EXPECTED_CHECKS}, got ${pass + fail}`);
}
console.log('\nLAYER PANEL REGRESSION: ' + pass + ' passed, ' + fail + ' failed, ' + broken + ' broken');
if (failures.length) { console.log('\nNeeds attention:'); failures.forEach((f) => console.log('  · ' + f)); }
process.exit(fail || broken ? 1 : 0);
