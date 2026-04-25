#!/usr/bin/env node
/**
 * sync-runtime-copies.js
 *
 * Keeps root-level Shokker Paint Booth (SPB) runtime assets in sync with
 * their mirrored copies under `electron-app/server` and
 * `electron-app/server/pyserver/_internal`.
 *
 * The root-level files are the canonical "source of truth". This script
 * copies drifted files from root → mirrored targets.
 *
 * USAGE
 *   node scripts/sync-runtime-copies.js --check          Report drift, do not modify.
 *   node scripts/sync-runtime-copies.js --write          Copy root → targets when drifted.
 *   node scripts/sync-runtime-copies.js --list           Enumerate every sync pair, no I/O.
 *   node scripts/sync-runtime-copies.js --check --verbose
 *   node scripts/sync-runtime-copies.js --write --dry-run   Show what --write would copy.
 *   node scripts/sync-runtime-copies.js --help
 *
 * FLAGS
 *   --check           Report-only mode. Drift is an error exit.
 *   --write           Copy drifted targets (non-destructive via atomic rename).
 *   --dry-run         With --write, show operations without performing them.
 *   --list            Enumerate manifest expansion, skip any disk checks.
 *   --verify          After --write, verify each target by SHA-256 hash.
 *   --verbose, -v     Extra logging (timing, per-file detail).
 *   --quiet, -q       Suppress informational output (errors still shown).
 *   --no-color        Disable ANSI color codes.
 *   --force           Ignore non-fatal safety checks (e.g. orphan warnings).
 *   --check-orphans   Scan targets for files present in targets but not the manifest.
 *   --history         Append a line to scripts/.runtime-sync-history.log after run.
 *   --config <path>   Alternate config file (default: scripts/.spbconfig.json).
 *   --manifest <path> Alternate manifest file (default: scripts/runtime-sync-manifest.json).
 *   --jobs <n>        Parallel copy worker count (default: 4).
 *   --help, -h        Print this help text.
 *
 * EXIT CODES
 *   0  Success (no drift, or drift fixed with --write).
 *   1  Hard error (missing source, failed copy, corrupt manifest, lock conflict).
 *   2  Warning (e.g. orphan copies found when --check-orphans is set).
 *
 * ENVIRONMENT OVERRIDES
 *   SPB_RUNTIME_MANIFEST    Overrides --manifest path.
 *   SPB_RUNTIME_VERBOSE=1   Enables verbose mode.
 *   SPB_RUNTIME_NO_COLOR=1  Disables color output.
 *   SPB_RUNTIME_HISTORY=1   Enables history log.
 *   NO_COLOR (any value)    Standard no-color env var (honored).
 *
 * EXAMPLES
 *   # Fail CI if any mirrored copy has drifted:
 *   node scripts/sync-runtime-copies.js --check
 *
 *   # Normal dev sync after editing a root-level .js file:
 *   node scripts/sync-runtime-copies.js --write
 *
 *   # Preview what --write would do without touching anything:
 *   node scripts/sync-runtime-copies.js --write --dry-run --verbose
 *
 *   # Audit for orphaned files under target dirs:
 *   node scripts/sync-runtime-copies.js --check --check-orphans
 *
 * PROGRAMMATIC API (kept backwards-compatible)
 *   const { loadManifest, listRuntimeSyncPairs, syncRuntimeCopies } =
 *     require('./scripts/sync-runtime-copies.js');
 */

'use strict';

const fs = require('fs');
const fsp = require('fs/promises');
const path = require('path');
const crypto = require('crypto');
const os = require('os');

// ---------------------------------------------------------------------------
// Paths & constants
// ---------------------------------------------------------------------------

const REPO_ROOT = path.resolve(__dirname, '..');
const DEFAULT_MANIFEST_PATH = path.join(__dirname, 'runtime-sync-manifest.json');
const DEFAULT_CONFIG_PATH = path.join(__dirname, '.spbconfig.json');
const HISTORY_LOG_PATH = path.join(__dirname, '.runtime-sync-history.log');
const LOCK_FILE_PATH = path.join(__dirname, '.runtime-sync.lock');

const DEFAULT_JOBS = 4;
const MAX_WINDOWS_PATH = 259; // MAX_PATH minus null terminator
const RETRY_ATTEMPTS = 3;
const RETRY_DELAY_MS = 120;

// ---------------------------------------------------------------------------
// Color / log helpers
// ---------------------------------------------------------------------------

/** Detect whether ANSI color is appropriate for the current stream. */
function supportsColor(stream) {
  if (process.env.NO_COLOR) return false;
  if (process.env.SPB_RUNTIME_NO_COLOR === '1') return false;
  if (!stream || !stream.isTTY) return false;
  return true;
}

/**
 * Build a palette. When color is disabled every function is the identity
 * function so callers can unconditionally write `color.red('x')`.
 */
function makePalette(enabled) {
  const wrap = (code) => (enabled ? (s) => `\x1b[${code}m${s}\x1b[0m` : (s) => String(s));
  return {
    gray: wrap('90'),
    red: wrap('31'),
    green: wrap('32'),
    yellow: wrap('33'),
    blue: wrap('34'),
    magenta: wrap('35'),
    cyan: wrap('36'),
    bold: wrap('1'),
  };
}

/** ISO-8601 timestamp with millisecond precision (local time). */
function nowStamp() {
  const d = new Date();
  const pad = (n, w = 2) => String(n).padStart(w, '0');
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}.${pad(d.getMilliseconds(), 3)}`
  );
}

/**
 * Create a leveled logger. Levels: debug < info < warn < error.
 * `quiet` suppresses info/debug; `verbose` enables debug.
 */
function createLogger({ verbose = false, quiet = false, color = null } = {}) {
  const palette = makePalette(color === null ? supportsColor(process.stdout) : !!color);
  const tag = palette.cyan('[runtime-sync]');
  const stamp = () => palette.gray(nowStamp());

  return {
    palette,
    debug(msg) {
      if (!verbose || quiet) return;
      console.log(`${stamp()} ${tag} ${palette.gray('debug')} ${msg}`);
    },
    info(msg) {
      if (quiet) return;
      console.log(`${stamp()} ${tag} ${palette.blue('info ')} ${msg}`);
    },
    ok(msg) {
      if (quiet) return;
      console.log(`${stamp()} ${tag} ${palette.green('ok   ')} ${msg}`);
    },
    warn(msg) {
      console.warn(`${stamp()} ${tag} ${palette.yellow('warn ')} ${msg}`);
    },
    error(msg) {
      console.error(`${stamp()} ${tag} ${palette.red('error')} ${msg}`);
    },
    raw(line) {
      if (quiet) return;
      console.log(line);
    },
  };
}

// ---------------------------------------------------------------------------
// CLI argument parsing
// ---------------------------------------------------------------------------

/**
 * Parse argv into a plain options object. Unknown flags become a fatal error
 * so typos fail loudly instead of silently no-op'ing.
 *
 * @param {string[]} argv
 * @returns {object}
 */
function parseArgs(argv) {
  const opts = {
    check: false,
    write: false,
    dryRun: false,
    list: false,
    verify: false,
    verbose: false,
    quiet: false,
    color: null,
    force: false,
    checkOrphans: false,
    history: false,
    help: false,
    manifestPath: null,
    configPath: null,
    jobs: null,
    unknown: [],
  };

  for (let i = 0; i < argv.length; i += 1) {
    const raw = argv[i];
    switch (raw) {
      case '--check':       opts.check = true; break;
      case '--write':       opts.write = true; break;
      case '--dry-run':     opts.dryRun = true; break;
      case '--list':        opts.list = true; break;
      case '--verify':      opts.verify = true; break;
      case '--verbose':
      case '-v':            opts.verbose = true; break;
      case '--quiet':
      case '-q':            opts.quiet = true; break;
      case '--no-color':    opts.color = false; break;
      case '--color':       opts.color = true; break;
      case '--force':       opts.force = true; break;
      case '--check-orphans': opts.checkOrphans = true; break;
      case '--history':     opts.history = true; break;
      case '--help':
      case '-h':            opts.help = true; break;
      case '--manifest':    opts.manifestPath = argv[++i] || null; break;
      case '--config':      opts.configPath = argv[++i] || null; break;
      case '--jobs':        opts.jobs = Number.parseInt(argv[++i], 10); break;
      default:
        if (raw && raw.startsWith('--')) opts.unknown.push(raw);
        else if (raw) opts.unknown.push(raw);
    }
  }

  return opts;
}

/** Apply environment variable overrides on top of CLI options. */
function applyEnvOverrides(opts) {
  if (process.env.SPB_RUNTIME_MANIFEST && !opts.manifestPath) {
    opts.manifestPath = process.env.SPB_RUNTIME_MANIFEST;
  }
  if (process.env.SPB_RUNTIME_VERBOSE === '1') opts.verbose = true;
  if (process.env.SPB_RUNTIME_NO_COLOR === '1') opts.color = false;
  if (process.env.SPB_RUNTIME_HISTORY === '1') opts.history = true;
  return opts;
}

/** Merge config file settings as lowest-priority defaults. */
function applyConfigFile(opts, configPath, logger) {
  const chosen = configPath || DEFAULT_CONFIG_PATH;
  if (!fs.existsSync(chosen)) return opts;
  let cfg;
  try {
    cfg = JSON.parse(fs.readFileSync(chosen, 'utf8'));
  } catch (err) {
    logger.warn(`config file ${chosen} is not valid JSON: ${err.message}`);
    return opts;
  }
  if (cfg && typeof cfg === 'object') {
    if (opts.jobs == null && Number.isFinite(cfg.jobs)) opts.jobs = cfg.jobs;
    if (!opts.manifestPath && typeof cfg.manifest === 'string') {
      opts.manifestPath = path.isAbsolute(cfg.manifest)
        ? cfg.manifest
        : path.resolve(path.dirname(chosen), cfg.manifest);
    }
    if (opts.color === null && typeof cfg.color === 'boolean') opts.color = cfg.color;
    if (!opts.verbose && cfg.verbose === true) opts.verbose = true;
    if (!opts.history && cfg.history === true) opts.history = true;
  }
  return opts;
}

/** Print the JSDoc header block as --help output. */
function printHelp() {
  try {
    const self = fs.readFileSync(__filename, 'utf8');
    const match = self.match(/\/\*\*([\s\S]*?)\*\//);
    if (match) {
      const body = match[1]
        .split('\n')
        .map((l) => l.replace(/^\s*\*\s?/, ''))
        .join('\n')
        .trim();
      console.log(body);
      return;
    }
  } catch (_) { /* fall through */ }
  console.log('sync-runtime-copies.js — keep SPB runtime mirrors in sync with repo root.');
}

// ---------------------------------------------------------------------------
// Manifest handling
// ---------------------------------------------------------------------------

/**
 * Load and validate the runtime-sync manifest.
 *
 * Accepted shape:
 *   {
 *     "source_of_truth": "repo_root",
 *     "targets": [ "<relDir>", ... ],
 *     "files":   [ "<relFile>", ... ],
 *     "version": "<optional semver or tag>"
 *   }
 *
 * @param {string} [manifestPath]
 * @returns {{files: string[], targets: string[], source_of_truth?: string, version?: string}}
 */
function loadManifest(manifestPath) {
  const p = manifestPath || DEFAULT_MANIFEST_PATH;
  if (!fs.existsSync(p)) {
    throw new Error(`Manifest not found at ${p}`);
  }
  const raw = fs.readFileSync(p, 'utf8');
  let manifest;
  try {
    manifest = JSON.parse(raw);
  } catch (err) {
    throw new Error(`Manifest at ${p} is not valid JSON: ${err.message}`);
  }
  validateManifestShape(manifest, p);
  return manifest;
}

/**
 * Assert the manifest looks well-formed. Gives actionable error messages
 * rather than generic "Invalid runtime sync manifest".
 */
function validateManifestShape(manifest, manifestPath) {
  if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
    throw new Error(`Manifest at ${manifestPath}: root must be an object`);
  }
  if (!Array.isArray(manifest.files)) {
    throw new Error(`Manifest at ${manifestPath}: "files" must be an array`);
  }
  if (!Array.isArray(manifest.targets)) {
    throw new Error(`Manifest at ${manifestPath}: "targets" must be an array`);
  }
  if (manifest.files.length === 0) {
    throw new Error(`Manifest at ${manifestPath}: "files" is empty — nothing to sync`);
  }
  if (manifest.targets.length === 0) {
    throw new Error(`Manifest at ${manifestPath}: "targets" is empty — no destinations`);
  }
  const badFile = manifest.files.find((f) => typeof f !== 'string' || !f.trim());
  if (badFile !== undefined) {
    throw new Error(`Manifest at ${manifestPath}: "files" entry ${JSON.stringify(badFile)} is not a non-empty string`);
  }
  const badTarget = manifest.targets.find((t) => typeof t !== 'string' || !t.trim());
  if (badTarget !== undefined) {
    throw new Error(`Manifest at ${manifestPath}: "targets" entry ${JSON.stringify(badTarget)} is not a non-empty string`);
  }
  // Detect duplicates which are almost always a copy-paste mistake.
  const seenFiles = new Set();
  for (const f of manifest.files) {
    const key = path.normalize(f);
    if (seenFiles.has(key)) throw new Error(`Manifest: duplicate file entry "${f}"`);
    seenFiles.add(key);
  }
  const seenTargets = new Set();
  for (const t of manifest.targets) {
    const key = path.normalize(t);
    if (seenTargets.has(key)) throw new Error(`Manifest: duplicate target entry "${t}"`);
    seenTargets.add(key);
  }
}

/**
 * Expand the manifest into concrete (source, target) pairs.
 * Each manifest file is replicated into every manifest target.
 *
 * @param {object} [manifest]
 * @returns {Array<{relFile:string, relTargetDir:string, sourceAbs:string, targetAbs:string, sourceRel:string, targetRel:string}>}
 */
function listRuntimeSyncPairs(manifest) {
  const m = manifest || loadManifest();
  const pairs = [];
  for (const relFile of m.files) {
    const sourceAbs = path.join(REPO_ROOT, relFile);
    for (const relTargetDir of m.targets) {
      // 2026-04-21 HEENAN POST-AUDIT: preserve subdirectory structure
      // when the manifest entry has one (e.g. `engine/compose.py`
      // should mirror to `<target>/engine/compose.py`, NOT flatten to
      // `<target>/compose.py`). Pre-fix used `path.basename(relFile)`
      // which silently flattened, a genuine footgun for Python modules
      // under `engine/`. Backward-compat: flat filenames (the original
      // front-end manifest list) are unchanged since relFile === basename.
      const targetAbs = path.join(REPO_ROOT, relTargetDir, relFile);
      pairs.push({
        relFile,
        relTargetDir,
        sourceAbs,
        targetAbs,
        sourceRel: relFile,
        targetRel: path.relative(REPO_ROOT, targetAbs),
      });
    }
  }
  return pairs;
}

// ---------------------------------------------------------------------------
// Filesystem utilities
// ---------------------------------------------------------------------------

/** Recursively create the parent directory for a file path. */
function ensureParentDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

/** Compute SHA-256 of a file, or null if the file is missing. */
async function hashFile(filePath) {
  try {
    const buf = await fsp.readFile(filePath);
    return crypto.createHash('sha256').update(buf).digest('hex');
  } catch (err) {
    if (err.code === 'ENOENT') return null;
    throw err;
  }
}

/**
 * Quick drift check. Uses size + mtime short-circuit before falling back to
 * a byte-for-byte comparison. Returns true iff the two files match.
 */
async function filesMatch(sourceAbs, targetAbs) {
  let srcStat;
  let tgtStat;
  try {
    srcStat = await fsp.stat(sourceAbs);
  } catch (err) {
    if (err.code === 'ENOENT') return false;
    throw err;
  }
  try {
    tgtStat = await fsp.stat(targetAbs);
  } catch (err) {
    if (err.code === 'ENOENT') return false;
    throw err;
  }
  if (srcStat.size !== tgtStat.size) return false;
  const [srcBuf, tgtBuf] = await Promise.all([fsp.readFile(sourceAbs), fsp.readFile(targetAbs)]);
  return srcBuf.equals(tgtBuf);
}

/** Warn if a path likely exceeds Windows' MAX_PATH. */
function checkPathLength(absPath, logger) {
  if (process.platform !== 'win32') return;
  if (absPath.length > MAX_WINDOWS_PATH) {
    logger.warn(`path exceeds Windows MAX_PATH (${absPath.length} > ${MAX_WINDOWS_PATH}): ${absPath}`);
  }
}

/** Warn if a path is a symlink; we overwrite symlinks explicitly. */
function checkSymlink(absPath, logger) {
  try {
    const st = fs.lstatSync(absPath);
    if (st.isSymbolicLink()) {
      logger.warn(`target is a symlink, will be replaced with a regular file: ${absPath}`);
    }
  } catch (_) { /* missing — fine */ }
}

/** Remove stale atomic-copy temp files from runtime target trees. */
function cleanupRuntimeTempArtifacts(manifest, logger) {
  const targets = Array.isArray(manifest.targets) ? manifest.targets : [];
  const stack = [];
  for (const targetRel of targets) {
    const targetAbs = path.resolve(REPO_ROOT, targetRel);
    if (fs.existsSync(targetAbs)) stack.push(targetAbs);
  }

  let removed = 0;
  while (stack.length > 0) {
    const dir = stack.pop();
    let entries = [];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch (_) {
      continue;
    }
    for (const entry of entries) {
      const abs = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        stack.push(abs);
      } else if (entry.isFile() && entry.name.includes('.tmp-')) {
        try {
          fs.unlinkSync(abs);
          removed += 1;
        } catch (err) {
          logger.warn(`could not remove stale runtime tmp artifact: ${abs} (${err.message})`);
        }
      }
    }
  }
  return removed;
}

/** Sleep helper for retry backoff. */
function sleep(ms) {
  return new Promise((res) => setTimeout(res, ms));
}

/** Windows sometimes blocks atomic replacement even when direct overwrite works. */
function isTransientCopyError(err) {
  return err && ['EBUSY', 'EPERM', 'EACCES', 'ENOTEMPTY'].includes(err.code);
}

/**
 * Atomically copy `src` onto `dest`:
 *   1. Write to `<dest>.tmp-<pid>-<rand>`
 *   2. Preserve mtime + mode
 *   3. fs.renameSync(tmp, dest)
 * Retries on EBUSY / EPERM / EACCES (Windows file lock churn).
 */
async function atomicCopy(src, dest, { preserveMtime = true, preserveMode = true } = {}) {
  ensureParentDir(dest);
  if (process.platform === 'win32') {
    await fsp.copyFile(src, dest);
    if (preserveMtime || preserveMode) {
      const srcStat = await fsp.stat(src);
      if (preserveMode) {
        try { await fsp.chmod(dest, srcStat.mode); } catch (_) { /* non-fatal on Windows */ }
      }
      if (preserveMtime) {
        try { await fsp.utimes(dest, srcStat.atime, srcStat.mtime); } catch (_) { /* non-fatal */ }
      }
    }
    return;
  }

  const tmp = `${dest}.tmp-${process.pid}-${crypto.randomBytes(4).toString('hex')}`;

  let lastErr;
  for (let attempt = 1; attempt <= RETRY_ATTEMPTS; attempt += 1) {
    try {
      const data = await fsp.readFile(src);
      await fsp.writeFile(tmp, data);
      if (preserveMtime || preserveMode) {
        const srcStat = await fsp.stat(src);
        if (preserveMode) {
          try { await fsp.chmod(tmp, srcStat.mode); } catch (_) { /* non-fatal on Windows */ }
        }
        if (preserveMtime) {
          try { await fsp.utimes(tmp, srcStat.atime, srcStat.mtime); } catch (_) { /* non-fatal */ }
        }
      }
      try {
        await fsp.rename(tmp, dest);
      } catch (renameErr) {
        if (!isTransientCopyError(renameErr)) throw renameErr;
        // Fallback for locked/guarded Windows paths where atomic replace is
        // denied but overwriting file contents is permitted by the sandbox.
        await fsp.copyFile(tmp, dest);
        try { await fsp.unlink(tmp); } catch (_) { /* best-effort cleanup */ }
      }
      return;
    } catch (err) {
      lastErr = err;
      // Clean the tmp file if it's lingering.
      try { await fsp.unlink(tmp); } catch (_) { /* ignore */ }
      const transient = isTransientCopyError(err);
      if (!transient || attempt === RETRY_ATTEMPTS) break;
      await sleep(RETRY_DELAY_MS * attempt);
    }
  }
  throw lastErr;
}

// ---------------------------------------------------------------------------
// Lock file
// ---------------------------------------------------------------------------

/**
 * Acquire an exclusive lock for the duration of a write run.
 * Prevents two processes racing (e.g. CI + dev build).
 */
function acquireLock(logger, { force = false } = {}) {
  const payload = { pid: process.pid, started: nowStamp(), released: null };
  if (fs.existsSync(LOCK_FILE_PATH)) {
    let prior = null;
    try {
      prior = JSON.parse(fs.readFileSync(LOCK_FILE_PATH, 'utf8'));
    } catch (_) { /* malformed lock is stale */ }
    const active = prior && !prior.released && isProcessAlive(Number(prior.pid));
    if (active && !force) {
      throw new Error(`another sync is running (lock file ${LOCK_FILE_PATH} exists); pass --force to override`);
    }
    if (active && force) {
      logger.warn(`active-looking lock ${LOCK_FILE_PATH} overridden via --force`);
    } else {
      logger.warn(`stale lock ${LOCK_FILE_PATH} reused`);
    }
  }
  try {
    fs.writeFileSync(LOCK_FILE_PATH, JSON.stringify(payload));
    return () => {
      try {
        fs.writeFileSync(LOCK_FILE_PATH, JSON.stringify({ ...payload, released: nowStamp() }));
      } catch (_) { /* lock release is best-effort */ }
    };
  } catch (err) {
    throw err;
  }
}

/** Best-effort process liveness check used for stale lock detection. */
function isProcessAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (_) {
    return false;
  }
}

// ---------------------------------------------------------------------------
// History log
// ---------------------------------------------------------------------------

/** Append a one-line JSON record of a run to the history log. */
function appendHistory(entry) {
  const line = JSON.stringify({ time: nowStamp(), ...entry });
  try {
    fs.appendFileSync(HISTORY_LOG_PATH, line + os.EOL);
  } catch (_) { /* history is best-effort */ }
}

// ---------------------------------------------------------------------------
// Orphan detection
// ---------------------------------------------------------------------------

/**
 * Walk each manifest target directory and return files whose basename matches
 * the .js/.css/.html pattern family but are NOT listed in the manifest.
 * These are likely stale copies from removed assets.
 */
function detectOrphans(manifest) {
  const managed = new Set(manifest.files.map((f) => path.basename(f)));
  const orphans = [];
  for (const relTarget of manifest.targets) {
    const absTarget = path.join(REPO_ROOT, relTarget);
    if (!fs.existsSync(absTarget)) continue;
    let entries;
    try {
      entries = fs.readdirSync(absTarget, { withFileTypes: true });
    } catch (_) { continue; }
    for (const ent of entries) {
      if (!ent.isFile()) continue;
      const base = ent.name;
      if (!/^(paint-booth-|fusion-|swatch-).*\.(js|css|html)$/.test(base)) continue;
      if (!managed.has(base)) {
        orphans.push(path.relative(REPO_ROOT, path.join(absTarget, base)));
      }
    }
  }
  return orphans;
}

// ---------------------------------------------------------------------------
// Parallel task runner
// ---------------------------------------------------------------------------

/**
 * Bounded parallel executor. Runs up to `limit` promises at once.
 * Returns results in input order.
 */
async function runLimited(items, limit, worker, { onProgress } = {}) {
  const results = new Array(items.length);
  let next = 0;
  let done = 0;
  const n = items.length;
  const concurrency = Math.max(1, Math.min(limit, n));

  async function pump() {
    while (next < n) {
      const idx = next++;
      try {
        results[idx] = await worker(items[idx], idx);
      } catch (err) {
        results[idx] = { __error: err };
      }
      done += 1;
      if (onProgress) onProgress(done, n);
    }
  }

  await Promise.all(Array.from({ length: concurrency }, pump));
  return results;
}

/** Simple [====    ] progress bar printed over a single line. */
function renderProgress(stream, done, total) {
  if (!stream || !stream.isTTY) return;
  const width = 24;
  const filled = Math.round((done / total) * width);
  const bar = '='.repeat(filled) + ' '.repeat(width - filled);
  stream.write(`\r[runtime-sync] [${bar}] ${done}/${total}`);
  if (done === total) stream.write('\n');
}

// ---------------------------------------------------------------------------
// Core sync function
// ---------------------------------------------------------------------------

/**
 * Sync root-level source files into their mirrored target copies.
 *
 * @param {object} [options]
 * @param {boolean} [options.write=false]       Apply fixes.
 * @param {boolean} [options.verbose=true]      Log per-file detail.
 * @param {boolean} [options.quiet=false]       Suppress all non-error output.
 * @param {boolean} [options.dryRun=false]      With write, print without doing.
 * @param {boolean} [options.verify=false]      Post-copy hash verification.
 * @param {boolean} [options.checkOrphans=false] Also scan for orphaned mirrors.
 * @param {boolean} [options.force=false]       Ignore non-fatal safety checks.
 * @param {boolean} [options.history=false]     Append history log entry.
 * @param {string}  [options.manifestPath]      Override manifest path.
 * @param {number}  [options.jobs]              Parallelism (default 4).
 * @param {object}  [options.logger]            Custom logger.
 * @returns {{checked:number, copied:number, drift:Array, driftCount:number,
 *            missingSources:string[], orphans:string[], elapsedMs:number,
 *            totalBytes:number, errors:Array}}
 */
async function syncRuntimeCopiesAsync(options = {}) {
  const {
    write = false,
    verbose = true,
    quiet = false,
    dryRun = false,
    verify = false,
    checkOrphans = false,
    history = false,
    manifestPath = null,
    jobs = DEFAULT_JOBS,
  } = options;

  const logger = options.logger || createLogger({ verbose, quiet });
  const startedAt = Date.now();

  const manifest = loadManifest(manifestPath);
  const pairs = listRuntimeSyncPairs(manifest);

  logger.debug(`manifest: ${pairs.length} sync pairs (${manifest.files.length} files × ${manifest.targets.length} targets)`);

  // Discover missing sources up front so we can fail fast with a clear message.
  const uniqueSources = new Set(pairs.map((p) => p.sourceAbs));
  const missingSources = [];
  for (const src of uniqueSources) {
    if (!fs.existsSync(src)) missingSources.push(path.relative(REPO_ROOT, src));
  }
  if (missingSources.length > 0) {
    for (const m of missingSources) {
      logger.error(`source file missing: ${m} (listed in manifest but not present at repo root)`);
    }
  }

  // Classify every pair (drift / in-sync / missing).
  const drift = [];
  const errors = [];
  let checked = 0;

  const classifyResults = await runLimited(
    pairs,
    Math.max(1, jobs),
    async (pair) => {
      if (!fs.existsSync(pair.sourceAbs)) return { pair, status: 'missing-source' };
      try {
        const same = await filesMatch(pair.sourceAbs, pair.targetAbs);
        return { pair, status: same ? 'in-sync' : 'drifted' };
      } catch (err) {
        return { pair, status: 'error', error: err };
      }
    },
  );

  for (const r of classifyResults) {
    checked += 1;
    if (r.__error) { errors.push({ kind: 'classify', error: r.__error }); continue; }
    if (r.status === 'drifted') drift.push(r.pair);
    if (r.status === 'error') errors.push({ kind: 'classify', pair: r.pair, error: r.error });
  }

  // Execute copy phase.
  let copied = 0;
  let totalBytes = 0;
  let tempArtifactsRemoved = 0;

  if (write && drift.length > 0) {
    logger.info(`${dryRun ? 'would copy' : 'copying'} ${drift.length} drifted file(s) with ${Math.max(1, jobs)} worker(s)`);
    const copyResults = await runLimited(
      drift,
      Math.max(1, jobs),
      async (pair) => {
        checkPathLength(pair.targetAbs, logger);
        checkSymlink(pair.targetAbs, logger);
        if (dryRun) {
          logger.debug(`dry-run: ${pair.sourceRel} -> ${pair.targetRel}`);
          return { pair, bytes: 0, hashOk: true, dryRun: true };
        }
        await atomicCopy(pair.sourceAbs, pair.targetAbs);
        let bytes = 0;
        try { bytes = (await fsp.stat(pair.targetAbs)).size; } catch (_) { /* ignore */ }
        let hashOk = true;
        if (verify) {
          const [srcHash, tgtHash] = await Promise.all([
            hashFile(pair.sourceAbs),
            hashFile(pair.targetAbs),
          ]);
          hashOk = !!srcHash && srcHash === tgtHash;
          if (!hashOk) {
            throw new Error(`hash mismatch after copy: ${pair.targetRel}`);
          }
        }
        return { pair, bytes, hashOk, dryRun: false };
      },
      { onProgress: (done, total) => {
          if (verbose && !quiet) renderProgress(process.stdout, done, total);
        } },
    );

    for (const r of copyResults) {
      if (r.__error) { errors.push({ kind: 'copy', error: r.__error }); continue; }
      if (!r.dryRun) copied += 1;
      totalBytes += r.bytes || 0;
      logger.debug(`${r.dryRun ? 'would copy' : 'copied'}: ${r.pair.sourceRel} -> ${r.pair.targetRel}${r.bytes ? ` (${r.bytes} B)` : ''}`);
    }
  }

  if (write && !dryRun) {
    tempArtifactsRemoved = cleanupRuntimeTempArtifacts(manifest, logger);
  }

  // Orphan scan.
  let orphans = [];
  if (checkOrphans) {
    orphans = detectOrphans(manifest);
    if (orphans.length > 0) {
      logger.warn(`${orphans.length} orphan file(s) found in target directories (not in manifest):`);
      for (const o of orphans) logger.warn(`  ${o}`);
    } else {
      logger.debug('no orphan files detected');
    }
  }

  // Summary.
  const elapsedMs = Date.now() - startedAt;
  if (!quiet) {
    logger.info(`checked ${checked} copy target(s) in ${elapsedMs} ms`);
    if (missingSources.length > 0) {
      logger.error(`missing sources: ${missingSources.join(', ')}`);
    }
    if (drift.length === 0) {
      logger.ok('no drift detected');
    } else if (write && !dryRun) {
      logger.ok(`synced ${copied}/${drift.length} drifted copy/copies (${totalBytes} bytes)`);
      if (tempArtifactsRemoved > 0) {
        logger.info(`removed ${tempArtifactsRemoved} stale runtime tmp artifact(s)`);
      }
    } else if (write && dryRun) {
      logger.info(`dry-run: ${drift.length} file(s) would be copied`);
    } else {
      logger.warn(`drift detected in ${drift.length} file(s):`);
      for (const pair of drift) logger.raw(`  ${pair.sourceRel} -> ${pair.targetRel}`);
    }
    if (errors.length > 0) {
      logger.error(`${errors.length} error(s) occurred during sync`);
      for (const e of errors) logger.error(`  [${e.kind}] ${e.error && e.error.message ? e.error.message : e.error}`);
    }
  }

  if (history) {
    appendHistory({
      mode: write ? (dryRun ? 'dry-run' : 'write') : 'check',
      checked,
      copied,
      drift: drift.length,
      missing: missingSources.length,
      orphans: orphans.length,
      errors: errors.length,
      elapsedMs,
      totalBytes,
      tempArtifactsRemoved,
      manifestVersion: manifest.version || null,
    });
  }

  return {
    checked,
    copied,
    drift,
    driftCount: drift.length,
    missingSources,
    orphans,
    elapsedMs,
    totalBytes,
    tempArtifactsRemoved,
    errors,
  };
}

/**
 * Synchronous wrapper for backwards compatibility with `copy-server-assets.js`
 * and any other caller that doesn't `await`. We block on a dedicated
 * `deasync`-free event-loop turn via `Atomics.wait`-style pattern using
 * `SharedArrayBuffer` is not available here, so we instead use a child-less
 * busy loop bound by the returned promise via `process.binding` tricks.
 *
 * To keep things simple and portable, we mirror the old synchronous behaviour
 * when `options.sync !== false`: perform the work synchronously using the
 * legacy code path (still correct, just single-threaded).
 */
function syncRuntimeCopies(options = {}) {
  const {
    write = false,
    verbose = true,
    quiet = false,
    dryRun = false,
    checkOrphans = false,
    history = false,
    manifestPath = null,
  } = options;

  const logger = options.logger || createLogger({ verbose, quiet });
  const startedAt = Date.now();

  const manifest = loadManifest(manifestPath);
  const pairs = listRuntimeSyncPairs(manifest);

  let checked = 0;
  let copied = 0;
  let totalBytes = 0;
  let tempArtifactsRemoved = 0;
  const drift = [];
  const missingSources = [];
  const errors = [];

  for (const pair of pairs) {
    checked += 1;
    if (!fs.existsSync(pair.sourceAbs)) {
      missingSources.push(pair.sourceRel);
      continue;
    }
    const srcBuf = fs.readFileSync(pair.sourceAbs);
    let tgtBuf = null;
    if (fs.existsSync(pair.targetAbs)) {
      try { tgtBuf = fs.readFileSync(pair.targetAbs); } catch (_) { tgtBuf = null; }
    }
    const inSync = tgtBuf && srcBuf.equals(tgtBuf);
    if (!inSync) {
      drift.push(pair);
      if (write && !dryRun) {
        try {
          ensureParentDir(pair.targetAbs);
          checkPathLength(pair.targetAbs, logger);
          checkSymlink(pair.targetAbs, logger);
          if (process.platform === 'win32') {
            fs.copyFileSync(pair.sourceAbs, pair.targetAbs);
            try {
              const st = fs.statSync(pair.sourceAbs);
              try { fs.chmodSync(pair.targetAbs, st.mode); } catch (_) { /* ignore on win32 */ }
              try { fs.utimesSync(pair.targetAbs, st.atime, st.mtime); } catch (_) { /* ignore */ }
            } catch (_) { /* ignore */ }
            copied += 1;
            totalBytes += srcBuf.length;
            continue;
          }
          // Atomic: write to tmp then rename.
          const tmp = `${pair.targetAbs}.tmp-${process.pid}-${crypto.randomBytes(4).toString('hex')}`;
          fs.writeFileSync(tmp, srcBuf);
          try {
            const st = fs.statSync(pair.sourceAbs);
            try { fs.chmodSync(tmp, st.mode); } catch (_) { /* ignore on win32 */ }
            try { fs.utimesSync(tmp, st.atime, st.mtime); } catch (_) { /* ignore */ }
          } catch (_) { /* ignore */ }
          try {
            fs.renameSync(tmp, pair.targetAbs);
          } catch (renameErr) {
            if (!isTransientCopyError(renameErr)) throw renameErr;
            fs.copyFileSync(tmp, pair.targetAbs);
            try { fs.unlinkSync(tmp); } catch (_) { /* best-effort cleanup */ }
          }
          copied += 1;
          totalBytes += srcBuf.length;
        } catch (err) {
          errors.push({ kind: 'copy', pair, error: err });
        }
      }
    }
  }

  if (write && !dryRun) {
    tempArtifactsRemoved = cleanupRuntimeTempArtifacts(manifest, logger);
  }

  let orphans = [];
  if (checkOrphans) {
    orphans = detectOrphans(manifest);
  }

  if (verbose && !quiet) {
    logger.info(`checked ${checked} copy targets in ${Date.now() - startedAt} ms`);
    if (missingSources.length > 0) {
      logger.error(`missing sources: ${missingSources.join(', ')}`);
    }
    if (drift.length === 0) {
      logger.ok('no drift detected');
    } else if (write && !dryRun) {
      logger.ok(`synced ${copied} drifted copy/copies (${totalBytes} bytes)`);
      if (tempArtifactsRemoved > 0) {
        logger.info(`removed ${tempArtifactsRemoved} stale runtime tmp artifact(s)`);
      }
    } else if (write && dryRun) {
      logger.info(`dry-run: ${drift.length} file(s) would be copied`);
    } else {
      logger.warn(`drift detected in ${drift.length} file(s):`);
      for (const pair of drift) logger.raw(`  ${pair.sourceRel} -> ${pair.targetRel}`);
    }
    if (orphans.length > 0) {
      logger.warn(`${orphans.length} orphan file(s): ${orphans.join(', ')}`);
    }
    if (errors.length > 0) {
      logger.error(`${errors.length} error(s) during sync`);
    }
  }

  if (history) {
    appendHistory({
      mode: write ? (dryRun ? 'dry-run' : 'write') : 'check',
      checked, copied,
      drift: drift.length,
      missing: missingSources.length,
      orphans: orphans.length,
      errors: errors.length,
      elapsedMs: Date.now() - startedAt,
      totalBytes,
      tempArtifactsRemoved,
      manifestVersion: manifest.version || null,
    });
  }

  return {
    checked,
    copied,
    drift,
    driftCount: drift.length,
    missingSources,
    orphans,
    elapsedMs: Date.now() - startedAt,
    totalBytes,
    tempArtifactsRemoved,
    errors,
  };
}

// ---------------------------------------------------------------------------
// CLI entry
// ---------------------------------------------------------------------------

async function main(argv) {
  const raw = parseArgs(argv);
  const opts = applyEnvOverrides(raw);
  const logger = createLogger({
    verbose: opts.verbose,
    quiet: opts.quiet,
    color: opts.color,
  });
  applyConfigFile(opts, opts.configPath, logger);

  if (opts.help) {
    printHelp();
    return 0;
  }

  if (opts.unknown && opts.unknown.length > 0) {
    logger.error(`unknown argument(s): ${opts.unknown.join(', ')}`);
    logger.error('try --help for usage');
    return 1;
  }

  // --list: enumerate without hitting disk.
  if (opts.list) {
    try {
      const manifest = loadManifest(opts.manifestPath);
      const pairs = listRuntimeSyncPairs(manifest);
      logger.info(`manifest has ${manifest.files.length} file(s) × ${manifest.targets.length} target(s) = ${pairs.length} pair(s)`);
      for (const p of pairs) logger.raw(`  ${p.sourceRel}  ->  ${p.targetRel}`);
      return 0;
    } catch (err) {
      logger.error(err.message);
      return 1;
    }
  }

  if (!opts.write && !opts.check) {
    logger.error('one of --check, --write, or --list is required');
    printHelp();
    return 1;
  }

  if (opts.write && opts.check) {
    logger.error('--write and --check are mutually exclusive');
    return 1;
  }

  // Lock only for real writes.
  let releaseLock = () => {};
  if (opts.write && !opts.dryRun) {
    try {
      releaseLock = acquireLock(logger, { force: opts.force });
    } catch (err) {
      logger.error(err.message);
      return 1;
    }
  }

  try {
    const result = await syncRuntimeCopiesAsync({
      write: opts.write,
      verbose: opts.verbose || !opts.quiet,
      quiet: opts.quiet,
      dryRun: opts.dryRun,
      verify: opts.verify,
      checkOrphans: opts.checkOrphans,
      history: opts.history,
      manifestPath: opts.manifestPath,
      jobs: Number.isFinite(opts.jobs) ? opts.jobs : DEFAULT_JOBS,
      logger,
    });

    if (result.missingSources.length > 0) return 1;
    if (result.errors.length > 0) return 1;
    if (opts.check && result.driftCount > 0) return 1;
    if (opts.checkOrphans && result.orphans.length > 0 && !opts.force) return 2;
    return 0;
  } catch (err) {
    logger.error(`fatal: ${err.message}`);
    if (opts.verbose && err.stack) logger.error(err.stack);
    return 1;
  } finally {
    releaseLock();
  }
}

if (require.main === module) {
  main(process.argv.slice(2)).then(
    (code) => process.exit(code),
    (err) => {
      console.error('[runtime-sync] unhandled:', err && err.stack ? err.stack : err);
      process.exit(1);
    },
  );
}

// ---------------------------------------------------------------------------
// Public API (kept backwards-compatible)
// ---------------------------------------------------------------------------

module.exports = {
  // Original exports:
  loadManifest,
  listRuntimeSyncPairs,
  syncRuntimeCopies,

  // New exports (opt-in):
  syncRuntimeCopiesAsync,
  validateManifestShape,
  detectOrphans,
  atomicCopy,
  hashFile,
  createLogger,
  parseArgs,
  REPO_ROOT,
  DEFAULT_MANIFEST_PATH,
};
