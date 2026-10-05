#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { runtimeSourceIdentity } = require('./spb_runtime_identity');

const ROOT = path.resolve(__dirname, '..');

function read(relativePath) {
    return fs.readFileSync(path.join(ROOT, relativePath), 'utf8');
}

function sha256(relativePath) {
    const absolute = path.join(ROOT, relativePath);
    if (!fs.existsSync(absolute)) return null;
    return crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex');
}

function run(name, exe, args, timeout = 120000) {
    const result = spawnSync(exe, args, {
        cwd: ROOT,
        encoding: 'utf8',
        timeout,
        maxBuffer: 32 * 1024 * 1024,
    });
    const output = ((result.stdout || '') + (result.stderr || '')).trim().split(/\r?\n/);
    return {
        name,
        ok: result.status === 0,
        exitCode: result.status,
        summary: output.filter(Boolean).slice(-4),
    };
}

const versionTxt = read('VERSION.txt').trim();
const packageVersion = JSON.parse(read('electron-app/package.json')).version;
const configSource = read('config.py');
const configVersionMatch = configSource.match(/^\s*VERSION:\s*str\s*=\s*"([^"]+)"/m);
const configBuildMatch = configSource.match(/^\s*BUILD_TAG:\s*str\s*=\s*"([^"]+)"/m);
const configVersion = configVersionMatch ? configVersionMatch[1] : null;
const configBuildTag = configBuildMatch ? configBuildMatch[1] : null;
const clientSource = read('paint-booth-5-api-render.js');
const clientVersionMatch = clientSource.match(/const CLIENT_VERSION = '([^']+)'/);
const clientVersion = clientVersionMatch ? clientVersionMatch[1] : null;
const configReleaseVersion = configVersion ? configVersion.replace(/-beta$/i, '') : null;
const versionConsistent = versionTxt === packageVersion
    && packageVersion === configReleaseVersion
    && packageVersion === configBuildTag
    && configVersion === clientVersion;

if (process.argv.includes('--check-version')) {
    const label = `VERSION.txt=${versionTxt}, package=${packageVersion}, config=${configVersion}, build=${configBuildTag}, client=${clientVersion}`;
    if (!versionConsistent) {
        console.error(`VERSION IDENTITY: inconsistent (${label})`);
        process.exit(1);
    }
    console.log(`VERSION IDENTITY: ${versionTxt} / ${configVersion} (${label})`);
    process.exit(0);
}
const head = spawnSync('git', ['rev-parse', 'HEAD'], { cwd: ROOT, encoding: 'utf8' });
const dirty = spawnSync('git', ['status', '--porcelain'], {
    cwd: ROOT,
    encoding: 'utf8',
    maxBuffer: 32 * 1024 * 1024,
});

const gates = [
    run('contextTargets', process.execPath, ['scripts/spb_context_target_lint.js']),
    run('layerManifest', process.execPath, ['scripts/spb_layer_regression.js', '--verify-plan']),
    run('easyManifest', process.execPath, ['scripts/spb_easy_regression.js', '--verify-plan']),
    run('easyFeatured', process.execPath, ['scripts/spb_easy_featured_audit.js']),
    run('releaseFixture', 'python', ['scripts/spb_release_fixture_audit.py']),
    run('releaseEvidence', process.execPath, ['scripts/spb_release_evidence_gate.js']),
    run('runtimeSync', process.execPath, ['scripts/sync-runtime-copies.js', '--check']),
    run('fileBudget', process.execPath, ['scripts/spb_file_budget.js', '--enforce']),
    run('generatedDrift', process.execPath, ['scripts/spb_generated_drift_guard.js', '--enforce']),
];

const criticalFiles = [
    'paint-booth-v2.html',
    'paint-booth-2-state-zones.js',
    'paint-booth-3-canvas.js',
    'paint-booth-5-api-render.js',
    'paint-booth-6-ui-boot.js',
    'js/features/spb-projects.js',
    'server.py',
    'server_v5.py',
    'runtime_identity_manifest.json',
    'shokker_engine_v2.py',
    'electron-app/main.js',
];
const hashes = {};
for (const relativePath of criticalFiles) {
    hashes[relativePath] = sha256(relativePath);
}

const requiredGatesPass = gates.every((gate) => gate.ok);
const evidenceRecorded = !!gates.find((gate) => gate.name === 'releaseEvidence' && gate.ok);
const output = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    canonicalRoot: ROOT,
    version: {
        versionTxt,
        packageVersion,
        configVersion,
        configBuildTag,
        clientVersion,
        consistent: versionConsistent,
    },
    source: {
        gitHead: head.status === 0 ? head.stdout.trim() : null,
        dirtyEntries: dirty.status === 0
            ? dirty.stdout.split(/\r?\n/).filter(Boolean).length
            : null,
        criticalSha256: hashes,
        runtimeIdentity: runtimeSourceIdentity(ROOT),
    },
    verification: {
        liveServerVerified: false,
        isolatedServerVerified: evidenceRecorded,
        restartRequired: evidenceRecorded ? 'not-applicable-isolated-child-stopped' : 'unknown-until-isolated-run',
        externalWritesDisabled: evidenceRecorded ? true : 'unverified-until-isolated-run',
        suiteExecution: evidenceRecorded ? 'verified-by-version-bound-evidence' : 'not-run-by-this-read-only-state-command',
        gates,
    },
    release: {
        eligible: versionConsistent && requiredGatesPass,
        blockers: [
            ...(!versionConsistent ? ['version identity is inconsistent'] : []),
            ...gates.filter((gate) => !gate.ok).map((gate) => gate.name + ' failed'),
        ],
    },
};

process.stdout.write(JSON.stringify(output, null, process.argv.includes('--compact') ? 0 : 2) + '\n');
