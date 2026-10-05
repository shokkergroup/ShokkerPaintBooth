'use strict';

// Build only the allowlisted demo payload, then place this Electron shell inside
// that generated stage. Nothing in the paid Electron server is a fallback.
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const DEMO_DIR = __dirname;
const REPO_ROOT = path.resolve(DEMO_DIR, '..');
const BUILDER = path.join(REPO_ROOT, 'demo', 'build_demo_stage.py');
const STAGE_DIR = path.join(DEMO_DIR, '.stage');
const STAGED_SERVER = path.join(STAGE_DIR, 'server');
const STAGED_ENTRYPOINT = path.join(STAGED_SERVER, 'demo_server.py');
const SOURCE_APP = path.join(DEMO_DIR, 'src');
const STAGED_APP = path.join(STAGE_DIR, 'app');

function fail(message) {
  console.error(`[shokk-demo-stage] ${message}`);
  process.exit(1);
}

function probe(command, prefixArgs) {
  const result = spawnSync(command, [...prefixArgs, '--version'], {
    cwd: REPO_ROOT,
    windowsHide: true,
    shell: false,
    encoding: 'utf8',
  });
  if (result.error && result.error.code === 'ENOENT') return false;
  return !result.error && result.status === 0;
}

function choosePython() {
  const configured = String(process.env.SPB_DEMO_PYTHON || '').trim();
  const candidates = configured
    ? [{ command: configured, prefixArgs: [] }]
    : process.platform === 'win32'
      ? [
          { command: 'py', prefixArgs: ['-3'] },
          { command: 'python', prefixArgs: [] },
        ]
      : [
          { command: 'python3', prefixArgs: [] },
          { command: 'python', prefixArgs: [] },
        ];

  for (const candidate of candidates) {
    if (probe(candidate.command, candidate.prefixArgs)) return candidate;
  }
  fail('Python 3 was not found. Set SPB_DEMO_PYTHON to a Python 3 executable.');
}

if (!fs.existsSync(BUILDER)) {
  fail(`Required stage builder is missing: ${BUILDER}`);
}
if (!fs.existsSync(path.join(SOURCE_APP, 'main.js')) ||
    !fs.existsSync(path.join(SOURCE_APP, 'preload.js'))) {
  fail('Electron shell sources are incomplete.');
}

const python = choosePython();
const build = spawnSync(
  python.command,
  [...python.prefixArgs, BUILDER, '--output', STAGE_DIR],
  {
    cwd: REPO_ROOT,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    windowsHide: true,
    shell: false,
    stdio: 'inherit',
  },
);

if (build.error) fail(`Stage builder could not start: ${build.error.message}`);
if (build.status !== 0) fail(`Stage builder failed with exit code ${build.status}.`);
if (!fs.existsSync(STAGED_ENTRYPOINT)) {
  fail(`Stage is missing required server entrypoint: ${STAGED_ENTRYPOINT}`);
}

fs.mkdirSync(STAGED_APP, { recursive: true });
for (const filename of ['main.js', 'preload.js']) {
  fs.copyFileSync(path.join(SOURCE_APP, filename), path.join(STAGED_APP, filename));
}

console.log(`[shokk-demo-stage] Ready: ${STAGE_DIR}`);
