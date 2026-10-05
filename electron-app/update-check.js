// update-check.js — Shokker Paint Booth in-app update banner module.
//
// Purpose: poll GitHub Releases API on launch and surface a small banner in
// the renderer when a newer version exists. This complements electron-updater
// (which silently fails on unsigned builds). We do NOT replace the existing
// auto-updater wiring — both run side-by-side. The owner controls when to
// yank electron-updater.
//
// Owner ships unsigned builds to PayHip customers (~60 users). Real
// auto-install needs a code-signing cert; until then, this module nudges
// the user to download the next release manually from GitHub.
//
// Public API:
//   checkForUpdate(currentVersion, options) -> Promise<{
//     updateAvailable: bool,
//     latestVersion: string,
//     releaseUrl: string,
//     releaseNotes: string,
//     reason?: string,   // when updateAvailable is false, why
//   }>
//
//   compareVersions(a, b) -> -1 | 0 | 1   (semver-ish; major.minor.patch)
//
//   isSnoozed(now, storage) -> bool
//   setSnooze(hours, storage) -> void
//
// All functions are safe to call in both Node (main process) and renderer
// contexts. `storage` defaults to globalThis.localStorage when available.

'use strict';

// Query the RELEASES LIST (not /releases/latest) so the banner finds the newest release even
// when it is marked "prerelease" — matching electron-updater's allowPrerelease=true. GitHub's
// /releases/latest silently skips prereleases + drafts, which would make an Alpha release
// invisible to the banner. Owner/repo casing matches package.json build.publish (shokkergroup).
const GITHUB_RELEASES_URL =
  'https://api.github.com/repos/shokkergroup/ShokkerPaintBooth/releases?per_page=20';
// Kept for backward-compat (older callers / tests may import this constant).
const GITHUB_LATEST_URL =
  'https://api.github.com/repos/shokkergroup/ShokkerPaintBooth/releases/latest';
const SNOOZE_KEY = 'spb_update_snooze_until';
const DEFAULT_TIMEOUT_MS = 8000;

// ----- version comparison -------------------------------------------------

/**
 * Parse a semver-ish version string into a {major, minor, patch, pre} tuple.
 * Tolerates leading "v" and prerelease tags. Missing pieces default to 0.
 * Returns null for unparseable input.
 */
function parseVersion(v) {
  if (typeof v !== 'string') return null;
  const cleaned = v.trim().replace(/^v/i, '');
  if (!cleaned) return null;
  const m = cleaned.match(/^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-+](.+))?$/);
  if (!m) return null;
  return {
    major: parseInt(m[1], 10) || 0,
    minor: parseInt(m[2] || '0', 10) || 0,
    patch: parseInt(m[3] || '0', 10) || 0,
    pre: m[4] || '',
  };
}

/**
 * Compare two semver-ish version strings.
 *   compareVersions('6.3.0', '6.2.0') ->  1
 *   compareVersions('6.2.9', '6.3.0') -> -1
 *   compareVersions('6.3.10', '6.3.9') -> 1
 *   compareVersions('6.3.0', '6.3.0') -> 0
 * Prerelease (e.g. "6.3.0-beta.1") is treated as LOWER than the same release
 * without prerelease ("6.3.0"), matching semver.
 * Unparseable inputs sort to 0 (treat as equal — safer than throwing).
 */
function compareVersions(a, b) {
  const pa = parseVersion(a);
  const pb = parseVersion(b);
  if (!pa || !pb) return 0;
  if (pa.major !== pb.major) return pa.major < pb.major ? -1 : 1;
  if (pa.minor !== pb.minor) return pa.minor < pb.minor ? -1 : 1;
  if (pa.patch !== pb.patch) return pa.patch < pb.patch ? -1 : 1;
  // prerelease sorts BEFORE release. A pre tag means lower precedence.
  if (pa.pre && !pb.pre) return -1;
  if (!pa.pre && pb.pre) return 1;
  if (pa.pre && pb.pre) {
    if (pa.pre === pb.pre) return 0;
    return pa.pre < pb.pre ? -1 : 1;
  }
  return 0;
}

// ----- snooze -------------------------------------------------------------

function resolveStorage(storage) {
  if (storage) return storage;
  if (typeof globalThis !== 'undefined' && globalThis.localStorage) {
    return globalThis.localStorage;
  }
  return null;
}

/**
 * Returns true if the user has snoozed the banner past `now`.
 * `now` defaults to Date.now(). Storage defaults to localStorage.
 */
function isSnoozed(now, storage) {
  const s = resolveStorage(storage);
  if (!s) return false;
  let raw;
  try { raw = s.getItem(SNOOZE_KEY); } catch (_) { return false; }
  if (!raw) return false;
  const until = Date.parse(raw);
  if (!Number.isFinite(until)) return false;
  const t = typeof now === 'number' ? now : Date.now();
  return until > t;
}

/**
 * Snooze the banner for `hours` (default 24). Stores ISO timestamp.
 */
function setSnooze(hours, storage) {
  const s = resolveStorage(storage);
  if (!s) return;
  const h = Number.isFinite(hours) && hours > 0 ? hours : 24;
  const until = new Date(Date.now() + h * 60 * 60 * 1000).toISOString();
  try { s.setItem(SNOOZE_KEY, until); } catch (_) {}
}

function clearSnooze(storage) {
  const s = resolveStorage(storage);
  if (!s) return;
  try { s.removeItem(SNOOZE_KEY); } catch (_) {}
}

// ----- GitHub fetch -------------------------------------------------------

function defaultFetch(url, timeoutMs) {
  // Prefer global fetch (Electron 33 has it in both main and renderer).
  // Fall back to https for older Node-only contexts.
  if (typeof fetch === 'function') {
    const controller = (typeof AbortController === 'function') ? new AbortController() : null;
    const opts = {
      method: 'GET',
      headers: {
        'User-Agent': 'ShokkerPaintBooth-UpdateCheck',
        'Accept': 'application/vnd.github+json',
      },
    };
    let timer = null;
    if (controller) {
      opts.signal = controller.signal;
      timer = setTimeout(() => { try { controller.abort(); } catch (_) {} }, timeoutMs);
    }
    return fetch(url, opts).then((res) => {
      if (timer) clearTimeout(timer);
      if (!res.ok) {
        const err = new Error('HTTP ' + res.status);
        err.status = res.status;
        throw err;
      }
      return res.json();
    }, (err) => {
      if (timer) clearTimeout(timer);
      throw err;
    });
  }
  // Node-only fallback.
  return new Promise((resolve, reject) => {
    let https;
    try { https = require('https'); } catch (e) { reject(e); return; }
    const req = https.request(url, {
      method: 'GET',
      headers: {
        'User-Agent': 'ShokkerPaintBooth-UpdateCheck',
        'Accept': 'application/vnd.github+json',
      },
    }, (res) => {
      let body = '';
      res.on('data', (c) => body += c);
      res.on('end', () => {
        if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
          try { resolve(JSON.parse(body)); }
          catch (e) { reject(e); }
        } else {
          const err = new Error('HTTP ' + res.statusCode);
          err.status = res.statusCode;
          reject(err);
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(timeoutMs, () => {
      try { req.destroy(new Error('TIMEOUT')); } catch (_) {}
    });
    req.end();
  });
}

// ----- release selection --------------------------------------------------

/**
 * Pick the release to compare against from a GitHub API response.
 *  - Array (the /releases LIST): return the highest-version NON-draft release.
 *    Prereleases ARE included (matches electron-updater allowPrerelease=true).
 *  - Object (a single release — legacy /releases/latest or a test mock): use it directly.
 * Returns null when nothing usable is present.
 */
function selectRelease(data) {
  if (Array.isArray(data)) {
    let best = null;
    let bestVer = null;
    for (const r of data) {
      if (!r || typeof r !== 'object' || r.draft) continue;
      const ver = String(r.tag_name || r.name || '').trim().replace(/^v/i, '');
      if (!ver || !parseVersion(ver)) continue;
      if (best === null || compareVersions(ver, bestVer) > 0) {
        best = r;
        bestVer = ver;
      }
    }
    return best;
  }
  if (data && typeof data === 'object') return data;
  return null;
}

// ----- main entry point ---------------------------------------------------

/**
 * Check GitHub for a newer release.
 *
 * @param {string} currentVersion  e.g. "6.3.0" — from package.json or
 *                                 app.getVersion(). Required.
 * @param {object} [options]
 * @param {function} [options.fetchImpl]  Inject a custom fetch (for tests).
 *                                        Must return a Promise<json>.
 * @param {object}   [options.storage]    Custom storage (default localStorage).
 * @param {boolean}  [options.ignoreSnooze]  If true, skip snooze check.
 * @param {number}   [options.timeoutMs]   Default 8000.
 * @returns {Promise<{updateAvailable: boolean, latestVersion: string,
 *                    releaseUrl: string, releaseNotes: string, reason?: string}>}
 *
 * Never throws — network/parse failures resolve with
 * `{updateAvailable: false, reason: 'network'}`.
 */
async function checkForUpdate(currentVersion, options) {
  const opts = options || {};
  const fetchImpl = opts.fetchImpl || defaultFetch;
  const timeoutMs = opts.timeoutMs || DEFAULT_TIMEOUT_MS;

  // Snooze check first — cheap, before any network call.
  if (!opts.ignoreSnooze && isSnoozed(Date.now(), opts.storage)) {
    return {
      updateAvailable: false,
      latestVersion: '',
      releaseUrl: '',
      releaseNotes: '',
      reason: 'snoozed',
    };
  }

  let data;
  try {
    data = await fetchImpl(opts.url || GITHUB_RELEASES_URL, timeoutMs);
  } catch (err) {
    // Silent on network failure — offline launches should not bother the user.
    return {
      updateAvailable: false,
      latestVersion: '',
      releaseUrl: '',
      releaseNotes: '',
      reason: 'network',
    };
  }

  // Accept either the /releases LIST (array) or a single release object (test mock / legacy
  // /releases/latest). From a list, pick the highest-version non-draft release.
  const release = selectRelease(data);
  if (!release || typeof release !== 'object') {
    return {
      updateAvailable: false,
      latestVersion: '',
      releaseUrl: '',
      releaseNotes: '',
      reason: 'invalid-response',
    };
  }

  // GitHub returns "tag_name": "v6.2.0" or "6.2.0".
  const tagName = String(release.tag_name || release.name || '').trim();
  const latestVersion = tagName.replace(/^v/i, '');
  if (!latestVersion) {
    return {
      updateAvailable: false,
      latestVersion: '',
      releaseUrl: '',
      releaseNotes: '',
      reason: 'no-tag',
    };
  }

  const cmp = compareVersions(latestVersion, currentVersion);
  const updateAvailable = cmp > 0;

  return {
    updateAvailable,
    latestVersion,
    releaseUrl: release.html_url ||
      'https://github.com/shokkergroup/ShokkerPaintBooth/releases/latest',
    releaseNotes: String(release.body || '').slice(0, 2000),
    reason: updateAvailable ? '' : 'up-to-date',
  };
}

// ----- exports ------------------------------------------------------------

const api = {
  checkForUpdate,
  compareVersions,
  parseVersion,
  selectRelease,
  isSnoozed,
  setSnooze,
  clearSnooze,
  SNOOZE_KEY,
  GITHUB_LATEST_URL,
  GITHUB_RELEASES_URL,
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = api;
}
// Also expose on globalThis when loaded as a plain <script>.
if (typeof globalThis !== 'undefined') {
  globalThis.SPBUpdateCheck = api;
}
