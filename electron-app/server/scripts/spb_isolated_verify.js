#!/usr/bin/env node
'use strict';

/**
 * Start the real V5 Flask app without touching the standing :59876 process,
 * prove its source/runtime identity and write kill-switch behavior, then run
 * the pinned Layer and/or Easy browser suites with fresh Chrome profiles.
 *
 *   node scripts/spb_isolated_verify.js --suite all
 *   node scripts/spb_isolated_verify.js --suite identity
 */

const crypto = require('crypto');
const fs = require('fs');
const net = require('net');
const path = require('path');
const { spawn, spawnSync } = require('child_process');
const { runtimeSourceIdentity, sha256File } = require('./spb_runtime_identity');

const ROOT = path.resolve(__dirname, '..');
const LIVE_PORT = 59876;

function arg(name, fallback) {
    const index = process.argv.indexOf('--' + name);
    return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function assert(condition, message) {
    if (!condition) throw new Error(message);
}

function normalizeWindowsPath(value) {
    assert(typeof value === 'string' && value.trim(), 'identity canonical_root is missing');
    const resolved = path.resolve(value.trim()).replace(/[\\/]+$/, '');
    return process.platform === 'win32' ? resolved.toLowerCase() : resolved;
}

function timestamp() {
    return new Date().toISOString().replace(/[:.]/g, '-');
}

function freePort() {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.unref();
        server.once('error', reject);
        server.listen(0, '127.0.0.1', () => {
            const port = server.address().port;
            server.close((error) => error ? reject(error) : resolve(port));
        });
    });
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function childStopped(child) {
    return !!child && (child.exitCode !== null || child.signalCode !== null);
}

function findPython() {
    const requested = process.env.SPB_PYTHON;
    const candidates = requested
        ? [[requested, []]]
        : (process.platform === 'win32'
            ? [['python', []], ['py', ['-3']]]
            : [['python3', []], ['python', []]]);
    for (const [exe, prefix] of candidates) {
        const probe = spawnSync(exe, [...prefix, '--version'], { encoding: 'utf8', windowsHide: true });
        if (probe.status === 0) return { exe, prefix };
    }
    throw new Error('No usable Python runtime found (set SPB_PYTHON)');
}

function appendBounded(state, chunk) {
    state.text += String(chunk || '');
    if (state.text.length > 256 * 1024) state.text = state.text.slice(-256 * 1024);
}

async function waitForBuildIdentity(baseUrl, serverChild, serverLog) {
    let lastError = 'server not ready';
    for (let attempt = 0; attempt < 300; attempt += 1) {
        if (childStopped(serverChild)) {
            throw new Error(`isolated server exited early (${serverChild.exitCode ?? serverChild.signalCode})\n${serverLog.text.slice(-4000)}`);
        }
        try {
            const response = await fetch(baseUrl + '/build-check', { signal: AbortSignal.timeout(2000) });
            if (response.ok) return await response.json();
            lastError = `HTTP ${response.status}`;
        } catch (error) {
            lastError = error.message;
        }
        await sleep(500);
    }
    throw new Error(`isolated server did not become ready: ${lastError}`);
}

function identityOf(payload) {
    return (payload && (payload.runtime_identity || payload.identity)) || payload || {};
}

function validateIdentity(payload, expected) {
    assert(payload && typeof payload === 'object', 'runtime identity payload is missing');
    const identity = identityOf(payload);
    assert(identity && typeof identity === 'object', 'runtime identity object is missing');
    assert(Number(identity.port) === expected.port, 'identity port does not match isolated port');
    assert(Number(identity.pid) === expected.pid, 'identity PID does not match spawned server');
    assert(identity.version === expected.version, 'identity version does not match config.py');
    if (identity !== payload) {
        if (payload.port != null) assert(Number(payload.port) === Number(identity.port), 'top-level and nested identity ports disagree');
        if (payload.pid != null) assert(Number(payload.pid) === Number(identity.pid), 'top-level and nested identity PIDs disagree');
        if (payload.version != null) assert(payload.version === identity.version, 'top-level and nested identity versions disagree');
    }
    assert(normalizeWindowsPath(identity.canonical_root) === normalizeWindowsPath(ROOT), 'identity canonical_root is not this workspace');
    assert(identity.external_writes_disabled === true, 'verification server did not report external writes disabled');
    assert(identity.server_hash === expected.serverHash, 'running server.py hash does not match this workspace');
    assert(identity.launcher_hash === expected.launcherHash, 'running server_v5.py hash does not match this workspace');
    assert(identity.source_hash === expected.sourceHash, 'runtime source_hash does not match its local manifest');
    assert(identity.source_hash_manifest === expected.manifest, 'runtime identity manifest path is wrong');
    assert(identity.source_hash_algorithm === expected.sourceHashAlgorithm, 'runtime source-hash algorithm is wrong');
    const sourceTuples = (rows) => Array.isArray(rows) ? rows.map((row) => [row.role, row.path, row.sha256]) : null;
    assert(JSON.stringify(sourceTuples(identity.source_hash_files)) === JSON.stringify(sourceTuples(expected.files)), 'runtime source file identity list is incomplete or changed');
    const started = identity.started_at || identity.start_time || identity.start_time_epoch;
    assert((typeof started === 'string' && Number.isFinite(Date.parse(started))) || Number(started) > 0, 'runtime start time is missing');
    return identity;
}

async function requestStatus(url, options) {
    const response = await fetch(url, { ...options, signal: AbortSignal.timeout(10000) });
    const text = await response.text();
    let body = null;
    try { body = text ? JSON.parse(text) : null; } catch (_) {}
    return { status: response.status, body, text: text.slice(0, 1000) };
}

async function securitySmoke(baseUrl) {
    const hostile = { Origin: 'https://attacker.example', Referer: 'https://attacker.example/x' };
    const local = { Origin: baseUrl, Referer: baseUrl + '/paint-booth-v2.html' };
    const checks = [];

    const foreignRead = await requestStatus(baseUrl + '/status', { headers: hostile });
    checks.push({ name: 'foreign sensitive read blocked', status: foreignRead.status, ok: foreignRead.status === 403 });

    const localRead = await requestStatus(baseUrl + '/status', { headers: local });
    checks.push({ name: 'matching local read allowed', status: localRead.status, ok: localRead.status === 200 });

    const mutatingGet = await requestStatus(baseUrl + '/api/clear-cache', { headers: local });
    checks.push({ name: 'mutating cache GET removed', status: mutatingGet.status, ok: [404, 405].includes(mutatingGet.status) });

    const foreignMutation = await requestStatus(baseUrl + '/api/clear-cache', {
        method: 'POST', headers: { ...hostile, 'Content-Type': 'application/json' }, body: '{}',
    });
    checks.push({ name: 'foreign mutation blocked', status: foreignMutation.status, ok: foreignMutation.status === 403 });

    const configWrite = await requestStatus(baseUrl + '/config', {
        method: 'POST', headers: { ...local, 'Content-Type': 'application/json' }, body: JSON.stringify({ car_paths: null }),
    });
    checks.push({ name: 'verification config write blocked', status: configWrite.status, ok: configWrite.status === 403 });

    const projectWrite = await requestStatus(baseUrl + '/api/projects/save/abort/spb-verification-no-session', {
        method: 'POST', headers: local,
    });
    checks.push({ name: 'verification Project mutation blocked', status: projectWrite.status, ok: projectWrite.status === 403 });

    return checks;
}

function runCaptured(exe, args, options, timeoutMs) {
    return new Promise((resolve) => {
        const child = spawn(exe, args, { ...options, windowsHide: true });
        let stdout = '';
        let stderr = '';
        child.stdout.on('data', (chunk) => {
            const text = String(chunk);
            stdout += text;
            process.stdout.write(text);
        });
        child.stderr.on('data', (chunk) => {
            const text = String(chunk);
            stderr += text;
            process.stderr.write(text);
        });
        const timer = setTimeout(() => {
            try { child.kill('SIGKILL'); } catch (_) {}
        }, timeoutMs);
        child.once('error', (error) => {
            clearTimeout(timer);
            resolve({ status: 1, stdout, stderr: stderr + '\n' + error.message, timedOut: false });
        });
        child.once('exit', (code, signal) => {
            clearTimeout(timer);
            resolve({ status: Number.isInteger(code) ? code : 1, signal, stdout, stderr, timedOut: signal === 'SIGKILL' });
        });
    });
}

async function stopChild(child) {
    if (!child || childStopped(child)) return true;
    try { child.kill('SIGTERM'); } catch (_) {}
    for (let i = 0; i < 20 && !childStopped(child); i += 1) await sleep(100);
    if (!childStopped(child)) {
        try { child.kill('SIGKILL'); } catch (_) {}
        for (let i = 0; i < 30 && !childStopped(child); i += 1) await sleep(100);
    }
    return childStopped(child);
}

function screenshotEvidence(directory) {
    if (!fs.existsSync(directory)) return [];
    return fs.readdirSync(directory)
        .filter((name) => name.toLowerCase().endsWith('.png'))
        .sort()
        .map((name) => {
            const file = path.join(directory, name);
            const stat = fs.statSync(file);
            return { name, bytes: stat.size, sha256: sha256File(file) };
        });
}

(async () => {
    const suite = String(arg('suite', 'all')).toLowerCase();
    assert(['all', 'layer', 'easy', 'identity'].includes(suite), '--suite must be all, layer, easy, or identity');
    const portIndex = process.argv.indexOf('--port');
    if (portIndex >= 0) assert(process.argv[portIndex + 1] && !process.argv[portIndex + 1].startsWith('--'), '--port requires a numeric value');
    const port = portIndex >= 0 ? Number(process.argv[portIndex + 1]) : await freePort();
    assert(Number.isInteger(port) && port > 1023 && port < 65536, 'invalid isolated port');
    assert(port !== LIVE_PORT, 'isolated verifier refuses live/developer port 59876');

    const configSource = fs.readFileSync(path.join(ROOT, 'config.py'), 'utf8');
    const versionMatch = configSource.match(/^\s*VERSION:\s*str\s*=\s*"([^"]+)"/m);
    assert(versionMatch, 'could not read config.py VERSION');
    const version = versionMatch[1];
    const sourceIdentity = runtimeSourceIdentity(ROOT);
    const evidenceDir = path.resolve(arg('out', path.join(ROOT, '_release_evidence', version.replace(/[^a-z0-9.-]/gi, '_'), 'isolated-' + timestamp())));
    fs.mkdirSync(evidenceDir, { recursive: true });

    const python = findPython();
    const serverLog = { text: '' };
    const env = {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        SHOKKER_PORT: String(port),
        SHOKKER_NO_CLEAN: '1',
        SPB_NO_LIVE_LINK: '1',
        SPB_ISOLATED_OUTPUT_DIR: path.join(evidenceDir, 'server-output'),
        SHOKKER_CRASH_LOG: path.join(evidenceDir, 'server-output', 'server_crashes.log'),
        SPB_NO_BOOT_SWATCH_WARM: '1',
    };
    const serverChild = spawn(python.exe, [...python.prefix, '-m', 'scripts.spb_run_isolated_server'], {
        cwd: ROOT,
        env,
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
    });
    serverChild.stdout.on('data', (chunk) => appendBounded(serverLog, chunk));
    serverChild.stderr.on('data', (chunk) => appendBounded(serverLog, chunk));
    const expectedIdentity = {
        port, pid: serverChild.pid, version,
        serverHash: sourceIdentity.serverHash, launcherHash: sourceIdentity.launcherHash,
        sourceHash: sourceIdentity.sourceHash, manifest: sourceIdentity.manifest,
        sourceHashAlgorithm: sourceIdentity.sourceHashAlgorithm, files: sourceIdentity.files,
    };

    const proof = {
        schemaVersion: 1,
        startedAt: new Date().toISOString(),
        version,
        suite,
        canonicalRoot: ROOT,
        port,
        serverPid: serverChild.pid,
        identity: null,
        securitySmoke: null,
        source: {},
        suites: [],
        ok: false,
    };
    let failed = false;
    try {
        const baseUrl = `http://127.0.0.1:${port}`;
        console.log(`ISOLATED SERVER: ${baseUrl} (PID ${serverChild.pid})`);
        const build = await waitForBuildIdentity(baseUrl, serverChild, serverLog);
        proof.identity = validateIdentity(build, expectedIdentity);

        const infoResponse = await requestStatus(baseUrl + '/api/server-info', {});
        assert(infoResponse.status === 200, `/api/server-info returned ${infoResponse.status}`);
        const infoIdentity = validateIdentity(infoResponse.body, expectedIdentity);
        assert(infoIdentity.source_hash === proof.identity.source_hash, 'identity endpoints disagree on source_hash');
        proof.securitySmoke = await securitySmoke(baseUrl);
        const smokeFailures = proof.securitySmoke.filter((item) => !item.ok);
        assert(!smokeFailures.length, 'runtime security smoke failed: ' + smokeFailures.map((item) => `${item.name}=${item.status}`).join(', '));
        console.log(`IDENTITY PASS: ${proof.identity.source_hash} external_writes_disabled=true`);

        const gitHead = spawnSync('git', ['rev-parse', 'HEAD'], { cwd: ROOT, encoding: 'utf8' });
        const candidate = spawnSync('git', ['status', '--porcelain=v1', '--untracked-files=all'], { cwd: ROOT, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 });
        const candidateRows = candidate.status === 0 ? candidate.stdout.split(/\r?\n/).filter(Boolean) : [];
        proof.source = {
            gitHead: gitHead.status === 0 ? gitHead.stdout.trim() : null,
            trackedClean: candidate.status === 0 && !candidateRows.some((row) => !row.startsWith('?? ')),
            candidateClean: candidate.status === 0 && candidateRows.length === 0,
            candidateEntries: candidate.status === 0 ? candidateRows.length : null,
            harnessHashes: {
                shot: sha256File(path.join(ROOT, 'scripts', 'spb_shot.js')),
                layerRunner: sha256File(path.join(ROOT, 'scripts', 'spb_layer_regression.js')),
                easyRunner: sha256File(path.join(ROOT, 'scripts', 'spb_easy_regression.js')),
                verifier: sha256File(__filename),
                isolatedServer: sha256File(path.join(ROOT, 'scripts', 'spb_run_isolated_server.py')),
                layerPlan: sha256File(path.join(ROOT, 'scripts', 'shotplans', 'layer-panel-regression.json')),
                easyPlan: sha256File(path.join(ROOT, 'scripts', 'shotplans', 'easy-mode-regression.json')),
            },
        };

        const specs = [];
        if (suite === 'all' || suite === 'layer') specs.push({ name: 'layer', runner: 'scripts/spb_layer_regression.js' });
        if (suite === 'all' || suite === 'easy') specs.push({ name: 'easy', runner: 'scripts/spb_easy_regression.js' });
        for (const spec of specs) {
            const cdpPort = await freePort();
            const outDir = path.join(evidenceDir, spec.name + '-shots');
            console.log(`\nRUN ${spec.name.toUpperCase()} SUITE (fresh CDP/profile ${cdpPort})`);
            const result = await runCaptured(
                process.execPath,
                [spec.runner, '--url', baseUrl + '/paint-booth-v2.html', '--out', outDir],
                { cwd: ROOT, env: { ...process.env, SPB_CDP_PORT: String(cdpPort) }, stdio: ['ignore', 'pipe', 'pipe'] },
                45 * 60 * 1000,
            );
            fs.writeFileSync(path.join(evidenceDir, spec.name + '.stdout.log'), result.stdout, 'utf8');
            fs.writeFileSync(path.join(evidenceDir, spec.name + '.stderr.log'), result.stderr, 'utf8');
            const row = {
                name: spec.name,
                exitCode: result.status,
                timedOut: result.timedOut,
                stdoutSha256: crypto.createHash('sha256').update(result.stdout).digest('hex'),
                stderrSha256: crypto.createHash('sha256').update(result.stderr).digest('hex'),
                screenshots: screenshotEvidence(outDir),
            };
            proof.suites.push(row);
            if (result.status !== 0) failed = true;
        }
        proof.ok = !failed;
    } catch (error) {
        failed = true;
        proof.error = error && error.stack ? error.stack : String(error);
        console.error('\nISOLATED VERIFY FAILED: ' + (error && error.message || error));
    } finally {
        proof.serverStopped = await stopChild(serverChild);
        if (!proof.serverStopped) {
            failed = true;
            proof.error = proof.error || 'isolated server could not be confirmed stopped';
        }
        proof.ok = !failed;
        proof.finishedAt = new Date().toISOString();
        proof.serverLogSha256 = crypto.createHash('sha256').update(serverLog.text).digest('hex');
        fs.writeFileSync(path.join(evidenceDir, 'server.log'), serverLog.text, 'utf8');
        fs.writeFileSync(path.join(evidenceDir, 'isolated-proof.json'), JSON.stringify(proof, null, 2) + '\n', 'utf8');
        console.log(`\nEVIDENCE: ${evidenceDir}`);
    }
    process.exit(failed ? 1 : 0);
})().catch((error) => {
    console.error('ISOLATED VERIFY FAILED: ' + (error && error.stack || error));
    process.exit(1);
});
