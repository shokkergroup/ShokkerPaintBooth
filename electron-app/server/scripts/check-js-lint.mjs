#!/usr/bin/env node
/*
 * check-js-lint.mjs - REPORT-ONLY ESLint quality net for the Paint Booth repo.
 * (WIN #11)
 *
 * The repo's only existing JS check is the package.json `check:js` script, which
 * runs `node --check` on the generated bundles (syntax only). This wrapper adds
 * a real, high-signal lint pass that surfaces ACTUAL bugs - duplicate object
 * keys, unreachable code, undefined references, NaN comparisons, duplicate
 * switch cases, etc. - without style noise.
 *
 * Config: ../eslint.config.js (ESLint FLAT config). The ESLint available in
 * this environment is v10, which only reads flat config (legacy .eslintrc /
 * .eslintignore are no longer supported), so this runner does NOT set
 * ESLINT_USE_FLAT_CONFIG. The flat config also carries the ignore patterns.
 *
 * Behaviour:
 *   - NEVER auto-fixes. There is no `--fix` anywhere. It only reports.
 *   - REPORT-ONLY by default: exits 0 even when lint problems are found, so it
 *     is safe to wire into CI / pre-commit before the baseline is clean.
 *     Pass `--strict` to propagate ESLint's exit code (any error -> non-zero).
 *   - Degrades gracefully: if ESLint cannot be found/run, it prints a clear
 *     install message and exits 0 (unless --strict).
 *
 * Resolution order for the ESLint binary:
 *   1. repo-local node_modules/.bin/eslint(.cmd)
 *   2. `npx --no-install eslint` (uses a globally/cached-installed ESLint)
 *   3. `npx eslint` (only with --allow-download: may fetch ESLint on first run)
 *
 * Usage:
 *   node scripts/check-js-lint.mjs            # report-only (exit 0 unless ESLint crashes)
 *   node scripts/check-js-lint.mjs --strict   # exit non-zero if ESLint reports problems
 *   node scripts/check-js-lint.mjs js scripts # lint only specific paths
 *   node scripts/check-js-lint.mjs --allow-download   # permit npx to fetch ESLint
 */

import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const isWin = process.platform === 'win32';

const rawArgs = process.argv.slice(2);
const STRICT = rawArgs.includes('--strict');
const ALLOW_DOWNLOAD = rawArgs.includes('--allow-download');
const targetArgs = rawArgs.filter((a) => a !== '--strict' && a !== '--allow-download');

// Default targets: the hand-written JS trees. The flat config's `ignores`
// further excludes generated bundles / dist / node_modules / _archive, and its
// `files` blocks decide which globals/parser apply per tree. Passing explicit
// paths (rather than '.') keeps the run fast and avoids walking asset dirs.
// In flat config there is no `--ext`; ESLint lints the .js/.mjs files matched
// by the config's `files` globs under these paths.
const DEFAULT_TARGETS = ['js', 'scripts', 'tools', 'electron-app'];
const targets = targetArgs.length ? targetArgs : DEFAULT_TARGETS;

const ESLINT_ARGS = ['--no-error-on-unmatched-pattern', ...targets];

const INSTALL_HINT = [
  'ESLint could not be run, so the JS lint quality net was SKIPPED.',
  '',
  'To enable it, install ESLint as a dev dependency:',
  '',
  '    npm install --save-dev eslint',
  '',
  'Then run:',
  '',
  '    node scripts/check-js-lint.mjs',
  '',
  'Notes:',
  '  - Config is eslint.config.js (FLAT config) at the repo root; it works with',
  '    ESLint v9 and v10 (the version this environment resolves via npx).',
  '  - This check never auto-fixes. It is report-only unless you pass --strict.',
  '  - To let this runner fetch ESLint on demand via npx, pass --allow-download.',
].join('\n');

function spawnEslint(cmd, args) {
  return spawnSync(cmd, args, {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: 'inherit',
    shell: isWin, // needed for .cmd / npx shims on Windows
    env: { ...process.env },
  });
}

function localBin() {
  const name = isWin ? 'eslint.cmd' : 'eslint';
  const p = join(ROOT, 'node_modules', '.bin', name);
  return existsSync(p) ? p : null;
}

// "Unavailable" = the binary itself could not be launched.
function looksUnavailable(res) {
  if (!res) return true;
  if (res.error && res.error.code === 'ENOENT') return true;
  if (res.status === 127) return true;
  return false;
}

// ESLint exit codes 0/1/2 all mean it actually ran (clean / problems / config
// error). We treat <=2 (and not unavailable) as "ran".
function ranSuccessfully(res) {
  return res && !res.error && res.status !== null && res.status >= 0 && res.status <= 2;
}

let res = null;
let ranReal = false;

const bin = localBin();
if (bin) {
  res = spawnEslint(bin, ESLINT_ARGS);
  ranReal = ranSuccessfully(res);
}

if (!ranReal) {
  const npx = isWin ? 'npx.cmd' : 'npx';
  const noInstall = spawnEslint(npx, ['--no-install', 'eslint', ...ESLINT_ARGS]);
  if (ranSuccessfully(noInstall) && !looksUnavailable(noInstall)) {
    res = noInstall;
    ranReal = true;
  } else if (ALLOW_DOWNLOAD) {
    const dl = spawnEslint(npx, ['--yes', 'eslint', ...ESLINT_ARGS]);
    if (ranSuccessfully(dl)) {
      res = dl;
      ranReal = true;
    } else {
      res = dl;
    }
  } else {
    res = noInstall;
  }
}

if (!ranReal) {
  process.stdout.write('\n[check-js-lint] SKIPPED\n' + INSTALL_HINT + '\n');
  process.exit(STRICT ? 1 : 0);
}

if (res.error) {
  process.stderr.write('[check-js-lint] failed to run ESLint: ' + res.error.message + '\n');
  process.exit(STRICT ? 1 : 0);
}

if (res.status === 2) {
  process.stderr.write(
    '[check-js-lint] ESLint exited 2 (configuration or internal error). ' +
      'If this persists, run `node scripts/check-js-lint.mjs --strict` to see details.\n',
  );
  process.exit(STRICT ? 2 : 0);
}

if (res.status === 1) {
  process.stdout.write(
    '\n[check-js-lint] ESLint reported problems above (report-only baseline).\n' +
      (STRICT ? '' : 'Run with --strict to make these fail the build.\n'),
  );
  process.exit(STRICT ? 1 : 0);
}

process.stdout.write('[check-js-lint] clean - no ESLint problems found.\n');
process.exit(0);
