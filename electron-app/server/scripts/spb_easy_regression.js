#!/usr/bin/env node
/**
 * spb_easy_regression.js — the standing Easy Mode regression sweep.
 *
 * Runs scripts/shotplans/easy-mode-regression.json through spb_shot.js, then
 * prints ONE verdict line per check instead of a wall of JSON. Every check
 * corresponds to a defect that was actually found and fixed — the point is that
 * a fix in one screen cannot silently break another.
 *
 *   node scripts/spb_easy_regression.js --url http://127.0.0.1:PORT/paint-booth-v2.html [--out DIR]
 *
 * Exit code 0 = all green, 1 = at least one FAIL (so it can gate a release).
 * The target URL is mandatory so this cannot silently use a stale :59876 app.
 */
const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

const HERE = __dirname;
const PLAN = path.join(HERE, 'shotplans', 'easy-mode-regression.json');
const EXPECTED_FULL_CHECKS = 114; // [SPB-EASY-STAGE2 2026-08-27] +4 R3 stage-geometry, +2 R9 narrow-stage
// [SPB-EASY-SHINE 2026-08-26] plan re-pinned: PAINT|SHINE labels, dynamic catalog-count check,
// fold>=15 (curated shelves lead) and families>=58 (post-consolidation) recalibrations.
const EXPECTED_PLAN_SHA256 = '92be020a61aa870d17363baad4a5858602cb5f98ad018a9718318cd1614f04e9';
const EXPECTED_FULL_SHOTS = [
    'R1-first-run-card', 'R2-pro-front-door', 'R3-catalog-landing', 'R4-search',
    'R5-full-catalog', 'R6-pick-a-finish', 'R7-by-color', 'R8-toast-and-keys',
    'R9-narrow-1100', 'R10-glossary-and-tour', 'R11-blending-math',
    'R12-undo-redo', 'R13-compare-and-map', 'R14-sculpt-destination',
    'R15-easy-to-pro-handoff', 'R16-toasts-speak-plain-english',
    'R17-iracing-number-is-correctable', 'R18-overlay-parity-sliders',
    'collections-shelves',
];
const outIdx = process.argv.indexOf('--out');
const OUT = outIdx > -1 ? process.argv[outIdx + 1]
    : path.join(HERE, '..', '_easy_gauntlet', 'shots', 'regression');
// --fast skips the shots that drive real engine renders. Those are the honest
// majority of the runtime (each waits seconds for a 2048 render to settle), and
// a gate nobody wants to wait for is a gate that stops being run. Use --fast
// while iterating; run the full sweep before shipping.
const FAST = process.argv.indexOf('--fast') > -1;
const urlIdx = process.argv.indexOf('--url');

if (!fs.existsSync(PLAN)) {
    console.error('FAIL  missing plan: ' + PLAN);
    process.exit(1);
}
const planSha256 = crypto.createHash('sha256').update(fs.readFileSync(PLAN)).digest('hex');
if (planSha256 !== EXPECTED_PLAN_SHA256) {
    console.error('FAIL  Easy plan bytes changed without updating the pinned manifest hash');
    console.error('expected: ' + EXPECTED_PLAN_SHA256);
    console.error('actual  : ' + planSha256);
    process.exit(1);
}
const fullPlan = JSON.parse(fs.readFileSync(PLAN, 'utf8'));
const fullPlanShotNames = fullPlan.map((shot) => shot.name);
if (JSON.stringify(fullPlanShotNames) !== JSON.stringify(EXPECTED_FULL_SHOTS)) {
    console.error('FAIL  Easy plan manifest changed without updating the pinned contract');
    console.error('expected: ' + EXPECTED_FULL_SHOTS.join(', '));
    console.error('actual  : ' + fullPlanShotNames.join(', '));
    process.exit(1);
}
if (process.argv.includes('--verify-plan')) {
    console.log(`EASY PLAN MANIFEST: ${EXPECTED_FULL_SHOTS.length} shots, ${EXPECTED_FULL_CHECKS} runtime checks pinned`);
    process.exit(0);
}
if (urlIdx < 0 || !process.argv[urlIdx + 1]) {
    console.error('FAIL  --url is required. Start an isolated SPB backend and pass its exact paint-booth URL.');
    console.error('      The standing runner will not default to the live/developer :59876 instance.');
    process.exit(2);
}

let planPath = PLAN;
let skipped = 0;
if (FAST) {
    const quick = fullPlan.filter((s) => !s.slow);
    skipped = fullPlan.length - quick.length;
    planPath = path.join(require('os').tmpdir(), 'spb-easy-regression-fast.json');
    fs.writeFileSync(planPath, JSON.stringify(quick), 'utf8');
}

const shotArgs = [path.join(HERE, 'spb_shot.js'), '--plan', planPath, '--out', OUT];
shotArgs.push('--url', process.argv[urlIdx + 1]);
const expectedShotNames = JSON.parse(fs.readFileSync(planPath, 'utf8')).map((shot) => shot.name);
const runStartedAt = Date.now();
const res = spawnSync(process.execPath,
    shotArgs,
    { encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 });

const stdout = (res.stdout || '') + (res.stderr || '');
const line = stdout.split('\n').find((l) => l.indexOf('JS [') === 0);
if (!line) {
    console.error(stdout.trim().split('\n').slice(-12).join('\n'));
    console.error('\nFAIL  the sweep produced no results (is the server on :59876?)');
    process.exit(1);
}

let shots;
try {
    shots = JSON.parse(line.slice(3));
} catch (e) {
    console.error('FAIL  could not parse results: ' + e.message);
    process.exit(1);
}

let pass = 0, fail = 0, broken = 0;
const failures = [];
const actualShotNames = shots.map((shot) => shot.name);
if (JSON.stringify(actualShotNames) !== JSON.stringify(expectedShotNames)) {
    broken++;
    failures.push('suite manifest mismatch: expected ' + expectedShotNames.join(', ') + '; got ' + actualShotNames.join(', '));
}
for (const shotName of expectedShotNames) {
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
    if (shot.shotError) {
        broken++;
        console.log('  BROKEN  shot failed: ' + shot.shotError);
        failures.push(shot.name + ' — shot failed: ' + shot.shotError);
        continue;
    }
    if (shot.jsThrew || shot.jsError) {
        broken++;
        const why = shot.jsThrew || shot.jsError;
        console.log('  BROKEN  step threw: ' + why);
        failures.push(shot.name + ' — step threw: ' + why);
        continue;
    }
    let checks;
    try {
        checks = JSON.parse(shot.js);
    } catch (e) {
        broken++;
        console.log('  BROKEN  unreadable result: ' + String(shot.js).slice(0, 120));
        failures.push(shot.name + ' — unreadable result');
        continue;
    }
    for (const c of checks) {
        const checkId = shot.name + '::' + c.k;
        if (checkIds.has(checkId)) {
            broken++;
            failures.push('duplicate check id: ' + checkId);
            continue;
        }
        checkIds.add(checkId);
        const detail = (c.detail === undefined || c.detail === null) ? '' : '  [' + c.detail + ']';
        if (c.pass) { pass++; console.log('  PASS  ' + c.k + detail); }
        else { fail++; console.log('  FAIL  ' + c.k + detail); failures.push(shot.name + ' — ' + c.k + detail); }
    }
}
if (!FAST && pass + fail !== EXPECTED_FULL_CHECKS) {
    broken++;
    failures.push('check-count mismatch: expected ' + EXPECTED_FULL_CHECKS + ', got ' + (pass + fail));
}

console.log('\n' + '='.repeat(60));
console.log('EASY MODE REGRESSION: ' + pass + ' passed, ' + fail + ' failed, ' + broken + ' broken step(s)');
if (FAST) console.log('FAST MODE — skipped ' + skipped + ' render-driving shot(s). Run without --fast before shipping.');
console.log('screenshots: ' + OUT);
if (failures.length) {
    console.log('\nNeeds attention:');
    failures.forEach((f) => console.log('  · ' + f));
}
process.exit(fail || broken ? 1 : 0);
