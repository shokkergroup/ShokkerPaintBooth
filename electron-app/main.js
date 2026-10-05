// main.js — Shokker Paint Booth Electron host.
// Improvements layered on top of the existing license + bundled-Python flow.
// PRESERVED: license/Payhip flow, bundled Python preference, zombie cleanup,
//            graceful shutdown, NSIS-friendly app behavior.

// ===== Memory budget for the main process (helps Chromium GC under load) =====
// Must be set before V8 initializes anything heavy (see app.commandLine below).

const electron = require('electron');
const { app, BrowserWindow, dialog, ipcMain, Menu, Tray, shell, session, nativeImage, crashReporter, powerSaveBlocker, screen } = electron;
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');
const fs = require('fs');
const os = require('os');
const https = require('https');
const http = require('http');
const crypto = require('crypto');
const { autoUpdater } = require('electron-updater');
const updateCheck = require('./update-check.js');

// ----- IMPROVEMENT #19: Bigger old-space for the main process under load -----
app.commandLine.appendSwitch('js-flags', '--max-old-space-size=4096');

// ----- IMPROVEMENT #33: Accessibility flags (screen-reader hints) -----
try { app.setAccessibilitySupportEnabled(true); } catch (_) { /* older electron */ }

// ----- IMPROVEMENT #34: GPU / hardware acceleration tuning -----
// On Windows, ANGLE D3D11 is the most stable backend for Chromium today.
app.commandLine.appendSwitch('use-angle', 'd3d11');
app.commandLine.appendSwitch('force_high_performance_gpu');
app.commandLine.appendSwitch('ignore-gpu-blocklist');
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('enable-accelerated-2d-canvas');
app.commandLine.appendSwitch('enable-webgl');
app.commandLine.appendSwitch('enable-zero-copy');
app.commandLine.appendSwitch('enable-features', 'CanvasOopRasterization,UseSkiaRenderer');
// Some integrated GPUs choke on hardware acceleration. The user can disable
// it by creating an empty file at %APPDATA%/ShokkerPaintBooth/disable-gpu.flag
const GPU_DISABLE_FLAG = path.join(process.env.APPDATA || os.homedir(), 'ShokkerPaintBooth', 'disable-gpu.flag');
let gpuDisabledByFlag = false;
try {
  if (fs.existsSync(GPU_DISABLE_FLAG)) {
    gpuDisabledByFlag = true;
    app.disableHardwareAcceleration();
    console.log('[GPU] Hardware acceleration disabled via flag file');
  }
} catch (_) { /* ignore */ }

// ----- IMPROVEMENT #15: Single-instance lock — prevent two SPB windows -----
// DEV ESCAPE HATCH: side-by-side dev sessions (e.g. alternate port, debug build)
// can bypass the lock with any of:
//   --allow-multiple-instances  CLI flag
//   SPB_ALLOW_MULTIPLE_INSTANCES=1  env var
//   SPB_DEV_PORT=<port>  env var (implies dev mode)
//   a sentinel file at %APPDATA%/ShokkerPaintBooth/allow-multiple-instances.flag
// The escape hatch is LOGGED so it is obvious in shipping/packaged bug reports
// when a second instance slipped through.
const _allowMultiByArg = Array.isArray(process.argv) && process.argv.some(a =>
  a === '--allow-multiple-instances' || a === '--allow-multiple' || a === '--multi-instance'
);
const _allowMultiByEnv = (process.env.SPB_ALLOW_MULTIPLE_INSTANCES === '1'
  || !!process.env.SPB_DEV_PORT
  || process.env.SPB_DEV_MODE === '1');
let _allowMultiByFlagFile = false;
try {
  const _multiFlagPath = path.join(process.env.APPDATA || os.homedir(), 'ShokkerPaintBooth', 'allow-multiple-instances.flag');
  _allowMultiByFlagFile = fs.existsSync(_multiFlagPath);
} catch (_) { /* ignore */ }
const DEV_ALLOW_MULTIPLE = _allowMultiByArg || _allowMultiByEnv || _allowMultiByFlagFile;

if (DEV_ALLOW_MULTIPLE) {
  console.log('[Lifecycle] Single-instance lock BYPASSED (dev mode) —',
    'arg=' + _allowMultiByArg, 'env=' + _allowMultiByEnv, 'flag=' + _allowMultiByFlagFile);
} else {
  const gotInstanceLock = app.requestSingleInstanceLock();
  if (!gotInstanceLock) {
    console.log('[Lifecycle] Another SPB instance is already running — quitting.');
    console.log('[Lifecycle] To allow multiple instances for development, use one of:');
    console.log('[Lifecycle]   --allow-multiple-instances  (CLI flag)');
    console.log('[Lifecycle]   SPB_ALLOW_MULTIPLE_INSTANCES=1  (env var)');
    console.log('[Lifecycle]   SPB_DEV_PORT=<port>  (env var, also implies alt port)');
    console.log('[Lifecycle]   touch %APPDATA%/ShokkerPaintBooth/allow-multiple-instances.flag');
    app.quit();
    process.exit(0);
  }
}

let mainWindow = null;
let rendererReadyForDeepLinks = false;
const pendingDeepLinks = [];
let finishViewerWindow = null;
let specSculptWindow = null;
let shokkDropWindow = null;
let shokkForgeWindow = null;
let iracingNativeHostWindow = null;
let iracingNativeTargetWindow = null;
let serverProcess = null;
let iracingBridgeProcess = null;
let iracingBridgeBuffer = '';
let iracingBridgeSeq = 1;
const iracingBridgePending = new Map();
const iracingNotifyHookedWindows = new WeakSet();
let iracingKoffiBridge = null;
// Production must keep one browser origin so localStorage/project state never
// appears to vanish behind an automatic port change. SPB_DEV_PORT remains the
// explicit, logged development escape hatch.
const STABLE_SERVER_PORT = 59876;
let serverPort = STABLE_SERVER_PORT;
let tray = null;
let splashWindow = null;
let serverReady = false;
let unsavedWork = false;
let quitInProgress = false;
let serverRestartCount = 0;
let serverRestartPromise = null;
const intentionalServerStops = new WeakSet();
let watchdogTimer = null;
let powerSaveBlockerId = null;

function wantsFinishViewerLaunch(argv = process.argv) {
  return Array.isArray(argv) && argv.some((arg) => {
    if (typeof arg !== 'string') return false;
    const value = arg.toLowerCase();
    return value === '--open-finish-viewer' || value === '--finish-viewer' || value === 'shokker://finish-viewer';
  });
}

function wantsSpecSculptLaunch(argv = process.argv) {
  return Array.isArray(argv) && argv.some((arg) => {
    if (typeof arg !== 'string') return false;
    const value = arg.toLowerCase();
    return value === '--open-spec-sculpt' || value === '--spec-sculpt' || value === 'shokker://spec-sculpt';
  });
}

// ===== IMPROVEMENT #20: Logs in %APPDATA%/spb/logs/ (rotating) =====
// DO NOT CHANGE THIS LITERAL OR ROUTE LICENSE THROUGH app.getPath("userData"). Every customer's license.dat lives here; changing it orphans ALL licenses. Any rename needs a migration that copies the old dir first.
const APP_DATA_DIR = path.join(process.env.APPDATA || os.homedir(), 'ShokkerPaintBooth');
const LOG_DIR = path.join(APP_DATA_DIR, 'logs');
const WINDOW_STATE_FILE = path.join(APP_DATA_DIR, 'window-state.json');
const RECENT_FILES_FILE = path.join(APP_DATA_DIR, 'recent-files.json');
try { if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR, { recursive: true }); } catch (_) {}

const LOG_FILE = path.join(LOG_DIR, `spb-${new Date().toISOString().substring(0, 10)}.log`);
// Legacy debug log path kept for the existing TIMEOUT dialog message
const DEBUG_LOG = path.join(os.tmpdir(), 'shokker-debug.log');

// Rotate: keep at most 10 daily logs.
function rotateLogs() {
  try {
    const files = fs.readdirSync(LOG_DIR)
      .filter((f) => f.startsWith('spb-') && f.endsWith('.log'))
      .sort()
      .reverse();
    for (let i = 10; i < files.length; i++) {
      try { fs.unlinkSync(path.join(LOG_DIR, files[i])); } catch (_) {}
    }
  } catch (_) {}
}
rotateLogs();

// [SPB LOG CAP 2026-08-28] the 2026-07-16 runaway (server crash -> 1s auto-restart loop, each
// cycle dumping full engine boot logs) grew spb-2026-07-16.log to 26.6 GB before anyone noticed.
// Hard-cap file logging per session; console output continues so live debugging still works.
const LOG_MAX_BYTES = 256 * 1024 * 1024;
let _logBytes = 0;
try { _logBytes = fs.existsSync(LOG_FILE) ? fs.statSync(LOG_FILE).size : 0; } catch (_) {}
let _logCapTripped = _logBytes > LOG_MAX_BYTES;
function debugLog(msg) {
  const ts = new Date().toISOString().substring(11, 23);
  const line = `[${ts}] ${msg}\n`;
  if (!_logCapTripped) {
    _logBytes += Buffer.byteLength(line);
    if (_logBytes > LOG_MAX_BYTES) {
      _logCapTripped = true;
      const capMsg = `[${ts}] [LOG CAP] 256MB reached — file logging suppressed for the rest of this session (runaway-log guard, see 2026-07-16 incident)\n`;
      try { fs.appendFileSync(LOG_FILE, capMsg); } catch (_) {}
      try { fs.appendFileSync(DEBUG_LOG, capMsg); } catch (_) {}
    } else {
      try { fs.appendFileSync(LOG_FILE, line); } catch (_) {}
      try { fs.appendFileSync(DEBUG_LOG, line); } catch (_) {}
    }
  }
  console.log(msg);
}
try { fs.writeFileSync(DEBUG_LOG, ''); } catch (_) {}
debugLog(`[Boot] SPB v${app.getVersion()} on ${process.platform} ${os.release()} (Electron ${process.versions.electron})`);
debugLog(`[GPU] Launch switches: angle=d3d11, forceHighPerformanceGpu, ignoreBlocklist, gpuRaster, accelerated2D, webgl, zeroCopy; disabledByFlag=${gpuDisabledByFlag}`);

// ===== IMPROVEMENT #21: Crash reporter for renderer/GPU process crashes =====
try {
  crashReporter.start({
    productName: 'ShokkerPaintBooth',
    companyName: 'Shokker Group',
    submitURL: 'https://localhost/_no_upload', // local-only; we just want dumps on disk
    uploadToServer: false,
    ignoreSystemCrashHandler: false,
    extra: { version: app.getVersion() },
  });
  debugLog(`[Crash] Reporter active. Dumps: ${app.getPath('crashDumps')}`);
} catch (e) {
  debugLog(`[Crash] Reporter init failed: ${e.message}`);
}

// ===== LICENSE KEY SYSTEM (preserved) =====
const LICENSE_DIR = APP_DATA_DIR;
const LICENSE_FILE = path.join(LICENSE_DIR, 'license.dat');
const ACTIVATION_GRACE_FILE = path.join(LICENSE_DIR, 'activation-grace.dat');
// ===== LICENSE SECRETS — loaded from a gitignored, build-bundled config (NOT hardcoded) =====
// The Payhip merchant secret, the AES key for the local license file, and the early-access
// password hashes live in spb-license-secrets.json (gitignored; bundled into app.asar via
// package.json "build.files"). Env vars override for dev. This keeps the secrets out of the
// PUBLIC SOURCE going forward. (The previously-hardcoded values are already public in git
// history + a shipped asar — rotating them and routing verify through an owner-hosted proxy
// remain owner-only tasks; see the readiness report B2/B3.)
function loadLicenseSecrets() {
  let cfg = {};
  try {
    const p = path.join(__dirname, 'spb-license-secrets.json');
    if (fs.existsSync(p)) cfg = JSON.parse(fs.readFileSync(p, 'utf8')) || {};
  } catch (e) {
    try { debugLog(`[License] Could not read spb-license-secrets.json: ${e.message}`); } catch (_) {}
  }
  return {
    encryptionKey: process.env.SPB_ENCRYPTION_KEY || cfg.encryptionKey || '',
    payhipProductSecret: process.env.SPB_PAYHIP_PRODUCT_SECRET || cfg.payhipProductSecret || '',
    earlyAccessHashes: Array.isArray(cfg.earlyAccessHashes)
      ? cfg.earlyAccessHashes.filter(h => typeof h === 'string' && h.length === 64)
      : []
  };
}
const LICENSE_SECRETS = loadLicenseSecrets();
const ENCRYPTION_KEY = LICENSE_SECRETS.encryptionKey;            // 32-byte AES-256 key (from config)
const PAYHIP_PRODUCT_SECRET = LICENSE_SECRETS.payhipProductSecret;
if (!ENCRYPTION_KEY || !PAYHIP_PRODUCT_SECRET) {
  try { debugLog('[License] WARNING: spb-license-secrets.json missing/incomplete — Payhip verify will not work in this build. (Early-access password unlock still works if hashes are present.)'); } catch (_) {}
}
const PAYHIP_VERIFY_BASE_URL = 'https://payhip.com/api/v2/license/verify';
const PAYHIP_USAGE_URL = 'https://payhip.com/api/v2/license/usage';
const LICENSE_REQUEST_TIMEOUT_MS = 10000;
const ACTIVATION_GRACE_MS = 3 * 24 * 60 * 60 * 1000;
const ACTIVATION_GRACE_CLOCK_SKEW_MS = 5 * 60 * 1000;

function isContributorTestBuild() {
  if (process.env.SPB_CONTRIBUTOR_BUILD === '1') return true;
  if (!app.isPackaged) return false;
  return fs.existsSync(path.join(__dirname, 'contributor-build.flag'));
}

// ===== DEVELOPER BYPASS (per-machine, irreversible by design) =====
// The plaintext code is intentionally NOT stored here. Only the SHA-256 hash.
const BYPASS_HASH = 'a8678ff0986fc7934df8f2bfad8debfd587e76b58c277e2eeaf2e6247135547f';

function getBypassFlagDir() {
  const base = process.platform === 'win32'
    ? (process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming'))
    : process.platform === 'darwin'
      ? path.join(os.homedir(), 'Library', 'Application Support')
      : path.join(os.homedir(), '.config');
  return path.join(base, 'shokker-paint-booth');
}

function getBypassFlagFile() {
  return path.join(getBypassFlagDir(), 'bypass.json');
}

function verifyBypassCode(code) {
  if (typeof code !== 'string' || code.length === 0) return false;
  const digest = crypto.createHash('sha256').update(code.trim(), 'utf8').digest('hex');
  // Accept the legacy developer hash OR any early-access password hash from the gitignored
  // config, so the owner can add / revoke passwords by editing spb-license-secrets.json with
  // no code change. All comparisons are SHA-256 hash vs hash — plaintext is never stored here.
  if (digest === BYPASS_HASH) return true;
  return LICENSE_SECRETS.earlyAccessHashes.includes(digest);
}

function writeBypassFlag() {
  try {
    const dir = getBypassFlagDir();
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    const payload = {
      enabled: true,
      activated_at: new Date().toISOString(),
      version: 1
    };
    fs.writeFileSync(getBypassFlagFile(), JSON.stringify(payload, null, 2), 'utf8');
    return true;
  } catch (e) {
    try { debugLog(`[License] Failed to write bypass flag: ${e.message}`); } catch (_) {}
    return false;
  }
}

function hasBypassFlag() {
  try {
    const file = getBypassFlagFile();
    if (!fs.existsSync(file)) return false;
    const raw = fs.readFileSync(file, 'utf8');
    const data = JSON.parse(raw);
    return data && data.enabled === true;
  } catch (e) {
    return false;
  }
}

function encryptData(data) {
  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipheriv('aes-256-cbc', Buffer.from(ENCRYPTION_KEY, 'utf8'), iv);
  let encrypted = cipher.update(JSON.stringify(data), 'utf8', 'hex');
  encrypted += cipher.final('hex');
  return iv.toString('hex') + ':' + encrypted;
}

function decryptData(raw) {
  try {
    const [ivHex, encrypted] = raw.split(':');
    const iv = Buffer.from(ivHex, 'hex');
    const decipher = crypto.createDecipheriv('aes-256-cbc', Buffer.from(ENCRYPTION_KEY, 'utf8'), iv);
    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    return JSON.parse(decrypted);
  } catch (e) {
    return null;
  }
}

function getMachineId() {
  return crypto.createHash('sha256')
    .update(os.hostname() + os.userInfo().username + os.homedir())
    .digest('hex').substring(0, 16);
}

function readLocalLicense() {
  try {
    if (!fs.existsSync(LICENSE_FILE)) return null;
    const raw = fs.readFileSync(LICENSE_FILE, 'utf8');
    const data = decryptData(raw);
    if (!data) return null;
    if (data.machineId !== getMachineId()) {
      console.log('[License] Machine ID mismatch - activation invalid on this device');
      return null;
    }
    return data;
  } catch (e) {
    console.log('[License] Failed to read local license:', e.message);
    return null;
  }
}

function saveLocalLicense(licenseKey, email, options = {}) {
  try {
    if (!fs.existsSync(LICENSE_DIR)) fs.mkdirSync(LICENSE_DIR, { recursive: true });
    const data = {
      licenseKey,
      email: email || '',
      machineId: getMachineId(),
      activatedAt: new Date().toISOString(),
      lastVerified: new Date().toISOString(),
      offlineActivated: !!options.offlineActivated,
      offlineReason: options.offlineReason || ''
    };
    fs.writeFileSync(LICENSE_FILE, encryptData(data), 'utf8');
    console.log(`[License] Activation saved locally${data.offlineActivated ? ' (offline rescue)' : ''}`);
    clearActivationGrace('activated');
    return true;
  } catch (e) {
    console.log('[License] Failed to save license:', e.message);
    return false;
  }
}

function clearActivationGrace(reason) {
  try {
    if (fs.existsSync(ACTIVATION_GRACE_FILE)) {
      fs.unlinkSync(ACTIVATION_GRACE_FILE);
      debugLog(`[License] Activation grace cleared (${reason || 'unspecified'})`);
    }
  } catch (e) {
    debugLog(`[License] Failed to clear activation grace: ${e.message}`);
  }
}

function readActivationGrace() {
  try {
    if (!fs.existsSync(ACTIVATION_GRACE_FILE)) return { exists: false, state: null };
    const raw = fs.readFileSync(ACTIVATION_GRACE_FILE, 'utf8');
    const state = decryptData(raw);
    if (!state || state.machineId !== getMachineId()) {
      return { exists: true, state: null, invalid: true };
    }
    return { exists: true, state };
  } catch (e) {
    debugLog(`[License] Failed to read activation grace: ${e.message}`);
    return { exists: true, state: null, invalid: true };
  }
}

function saveActivationGrace(state) {
  try {
    if (!fs.existsSync(LICENSE_DIR)) fs.mkdirSync(LICENSE_DIR, { recursive: true });
    fs.writeFileSync(ACTIVATION_GRACE_FILE, encryptData(state), 'utf8');
    return true;
  } catch (e) {
    debugLog(`[License] Failed to save activation grace: ${e.message}`);
    return false;
  }
}

function getActivationGraceStatus(state, nowMs = Date.now()) {
  if (!state) return { active: false, expired: true, reason: 'missing' };
  const startedMs = Date.parse(state.startedAt || '');
  const expiresMs = Date.parse(state.expiresAt || '');
  const lastSeenMs = Date.parse(state.lastSeenAt || state.startedAt || '');
  if (!Number.isFinite(startedMs) || !Number.isFinite(expiresMs) || !Number.isFinite(lastSeenMs)) {
    return { active: false, expired: true, reason: 'invalid-dates' };
  }
  if (nowMs + ACTIVATION_GRACE_CLOCK_SKEW_MS < lastSeenMs) {
    return { active: false, expired: true, reason: 'clock-rollback' };
  }
  const remainingMs = expiresMs - nowMs;
  if (remainingMs <= 0) {
    return { active: false, expired: true, reason: 'expired', remainingMs: 0 };
  }
  return { active: true, expired: false, remainingMs };
}

function startOrContinueActivationGrace(reason) {
  const existing = readActivationGrace();
  const nowMs = Date.now();

  if (existing.exists) {
    const status = getActivationGraceStatus(existing.state, nowMs);
    if (!status.active) {
      debugLog(`[License] Activation grace unavailable: ${status.reason || 'expired'}`);
      return false;
    }
    existing.state.lastSeenAt = new Date(nowMs).toISOString();
    existing.state.lastReason = reason || existing.state.lastReason || '';
    saveActivationGrace(existing.state);
    debugLog(`[License] Activation grace active; ${Math.ceil(status.remainingMs / (60 * 60 * 1000))}h remaining`);
    return true;
  }

  const state = {
    machineId: getMachineId(),
    startedAt: new Date(nowMs).toISOString(),
    expiresAt: new Date(nowMs + ACTIVATION_GRACE_MS).toISOString(),
    lastSeenAt: new Date(nowMs).toISOString(),
    lastReason: reason || ''
  };
  if (!saveActivationGrace(state)) return false;
  debugLog('[License] Activation grace started; 72h remaining');
  return true;
}

function hasActiveActivationGrace() {
  const existing = readActivationGrace();
  if (!existing.exists) return false;
  const status = getActivationGraceStatus(existing.state);
  if (!status.active) {
    debugLog(`[License] Activation grace not active: ${status.reason || 'expired'}`);
    return false;
  }
  existing.state.lastSeenAt = new Date().toISOString();
  saveActivationGrace(existing.state);
  debugLog(`[License] Activation grace startup allowed; ${Math.ceil(status.remainingMs / (60 * 60 * 1000))}h remaining`);
  return true;
}

function summarizePayhipBody(body) {
  const text = String(body || '').replace(/\s+/g, ' ').trim();
  return text.length > 240 ? text.substring(0, 240) + '...' : text;
}

function parsePayhipVerifyResponse(statusCode, body, transport) {
  let json = null;
  try {
    json = JSON.parse(body || '{}');
  } catch (e) {
    debugLog(`[License] Payhip verify ${transport} returned non-JSON status=${statusCode} body="${summarizePayhipBody(body)}"`);
    return { valid: false, reason: `Invalid response from license server (HTTP ${statusCode || 'unknown'}).` };
  }

  debugLog(`[License] Payhip verify ${transport} status=${statusCode} error=${!!json.error} dataType=${Array.isArray(json.data) ? 'array' : typeof json.data}`);

  if (statusCode >= 500) {
    return { valid: false, reason: `License server error (HTTP ${statusCode}). Please try again.` };
  }

  if (json.data && !Array.isArray(json.data) && json.data.enabled) {
    return {
      valid: true,
      email: json.data.buyer_email || '',
      uses: json.data.uses || 0,
      productName: json.data.product_name || ''
    };
  }

  if (statusCode === 401 || statusCode === 403) {
    return { valid: false, reason: `License server rejected SPB activation credentials (HTTP ${statusCode}). Contact support.` };
  }

  return { valid: false, reason: 'License key is disabled or invalid' };
}

function formatPayhipNetworkReason(error, transport) {
  const code = (error && (error.code || error.name)) ? String(error.code || error.name) : 'NETWORK';
  const message = error && error.message ? String(error.message).replace(/\s+/g, ' ').trim() : 'request failed';
  debugLog(`[License] Payhip ${transport} network failure code=${code} message=${message}`);
  return {
    valid: false,
    networkError: true,
    reason: `Could not reach license server (${code}). Check your internet/firewall, then send the SPB log if it keeps happening.`
  };
}

function payhipVerifyUrl(licenseKey) {
  return `${PAYHIP_VERIFY_BASE_URL}?license_key=${encodeURIComponent(licenseKey)}`;
}

function requestPayhipViaHttps(url, redirectCount = 0) {
  return new Promise((resolve) => {
    // license-verify-hang-fix 2026-06-07: req.setTimeout is socket-only and does
    // not cover a DNS/getaddrinfo or TCP-connect hang (the timer arms only after a
    // socket is assigned). On a blackholed/captive network the request never errors
    // and this Promise would never resolve, gating the electron:net fallback AND the
    // offline-activation path -> dialog stuck on 'Verifying...'. The hard wall-clock
    // guard below guarantees exactly one resolution so the offline-activation
    // fallback always engages.
    let settled = false;
    const finish = (v) => {
      if (settled) return;
      settled = true;
      clearTimeout(guard);
      resolve(v);
    };
    const guard = setTimeout(() => {
      const timeoutError = new Error('request timed out (guard)');
      timeoutError.code = 'TIMEOUT';
      try { req.destroy(timeoutError); } catch (_) {}
      finish({ ok: false, transport: 'node:https', error: timeoutError });
    }, LICENSE_REQUEST_TIMEOUT_MS + 500);
    const req = https.request(url, {
      method: 'GET',
      headers: {
        'product-secret-key': PAYHIP_PRODUCT_SECRET,
        'User-Agent': `ShokkerPaintBooth/${app.getVersion()}`
      }
    }, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        const location = res.headers && res.headers.location;
        if (location && res.statusCode >= 300 && res.statusCode < 400 && redirectCount < 3) {
          const nextUrl = new URL(location, url).toString();
          debugLog(`[License] Payhip node:https redirect status=${res.statusCode}`);
          requestPayhipViaHttps(nextUrl, redirectCount + 1).then(finish);
          return;
        }
        finish({ ok: true, transport: 'node:https', statusCode: res.statusCode || 0, body });
      });
    });
    req.on('error', (err) => {
      finish({ ok: false, transport: 'node:https', error: err });
    });
    req.setTimeout(LICENSE_REQUEST_TIMEOUT_MS, () => {
      const timeoutError = new Error('request timed out');
      timeoutError.code = 'TIMEOUT';
      try { req.destroy(timeoutError); } catch (_) {}
      finish({ ok: false, transport: 'node:https', error: timeoutError });
    });
    req.end();
  });
}

function requestPayhipViaElectronNet(url) {
  return new Promise((resolve) => {
    try {
      if (!electron.net || (typeof electron.net.isOnline === 'function' && !electron.net.isOnline())) {
        const offlineError = new Error('electron:net reports offline');
        offlineError.code = 'OFFLINE';
        resolve({ ok: false, transport: 'electron:net', error: offlineError });
        return;
      }
      const req = electron.net.request({ method: 'GET', url, redirect: 'follow' });
      req.setHeader('product-secret-key', PAYHIP_PRODUCT_SECRET);
      req.setHeader('User-Agent', `ShokkerPaintBooth/${app.getVersion()}`);
      let body = '';
      const timer = setTimeout(() => {
        try { req.abort(); } catch (_) {}
        const timeoutError = new Error('request timed out');
        timeoutError.code = 'TIMEOUT';
        resolve({ ok: false, transport: 'electron:net', error: timeoutError });
      }, LICENSE_REQUEST_TIMEOUT_MS);
      req.on('response', (response) => {
        response.on('data', (chunk) => { body += chunk.toString(); });
        response.on('end', () => {
          clearTimeout(timer);
          resolve({ ok: true, transport: 'electron:net', statusCode: response.statusCode || 0, body });
        });
      });
      req.on('error', (err) => {
        clearTimeout(timer);
        resolve({ ok: false, transport: 'electron:net', error: err });
      });
      req.end();
    } catch (err) {
      resolve({ ok: false, transport: 'electron:net', error: err });
    }
  });
}

async function verifyWithPayhip(licenseKey) {
  const url = payhipVerifyUrl(licenseKey);

  async function runVerify() {
    const first = await requestPayhipViaHttps(url);
    if (first.ok) return parsePayhipVerifyResponse(first.statusCode, first.body, first.transport);

    debugLog(`[License] Retrying Payhip verify through electron:net after ${first.transport} failed: ${first.error && first.error.message ? first.error.message : 'unknown error'}`);
    const second = await requestPayhipViaElectronNet(url);
    if (second.ok) return parsePayhipVerifyResponse(second.statusCode, second.body, second.transport);

    const secondReason = formatPayhipNetworkReason(second.error, second.transport);
    secondReason.firstError = first.error && first.error.message ? first.error.message : String(first.error || '');
    return secondReason;
  }

  // license-verify-hang-fix 2026-06-07: belt-and-suspenders overall guard. Even if a
  // transport hangs past its own timer, verify can never exceed ~2*timeout + buffer.
  // Resolving with networkError:true engages the dialog's offline-activation branch so
  // the user always gets in on a dead/captive network.
  let overallTimer = null;
  const overallGuard = new Promise((resolve) => {
    overallTimer = setTimeout(() => {
      debugLog('[License] verifyWithPayhip overall guard fired — falling back to offline activation.');
      resolve({
        valid: false,
        networkError: true,
        reason: 'License server timed out. Saved offline activation on this PC.'
      });
    }, 2 * LICENSE_REQUEST_TIMEOUT_MS + 2000);
  });

  try {
    return await Promise.race([runVerify(), overallGuard]);
  } finally {
    if (overallTimer) clearTimeout(overallTimer);
  }
}

function incrementPayhipUsage(licenseKey) {
  return new Promise((resolve) => {
    const postData = JSON.stringify({ license_key: licenseKey });
    const req = https.request(PAYHIP_USAGE_URL, {
      method: 'PUT',
      headers: {
        'product-secret-key': PAYHIP_PRODUCT_SECRET,
        'Content-Type': 'application/json',
        'Content-Length': postData.length,
        'User-Agent': `ShokkerPaintBooth/${app.getVersion()}`
      }
    }, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => resolve(true));
    });
    req.on('error', () => resolve(false));
    req.setTimeout(LICENSE_REQUEST_TIMEOUT_MS, () => { req.destroy(); resolve(false); });
    req.write(postData);
    req.end();
  });
}

function showLicenseDialog() {
  return new Promise((resolve) => {
    let resolved = false;
    function safeResolve(val) {
      if (resolved) return;
      resolved = true;
      resolve(val);
    }

    const licenseWin = new BrowserWindow({
      width: 520,
      height: 420,
      resizable: false,
      minimizable: false,
      maximizable: false,
      title: 'Shokker Paint Booth - Activate',
      backgroundColor: '#0a0a0a',
      autoHideMenuBar: true,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: false,
        preload: path.join(__dirname, 'license-preload.js')
      }
    });

    debugLog('[Dialog] License window created, loading license.html');

    ipcMain.once('license-submit', async (_event, key) => {
      debugLog(`[Dialog] Received license-submit with key: ${(key || '').substring(0, 5)}...`);
      const trimmedKey = (key || '').trim();
      if (!trimmedKey) {
        licenseWin.webContents.send('license-error', 'Please enter a license key.');
        ipcMain.once('license-submit', arguments.callee);
        return;
      }

      licenseWin.webContents.send('license-status', 'Verifying...');

      const result = await verifyWithPayhip(trimmedKey);
      if (result.valid) {
        await incrementPayhipUsage(trimmedKey);
        saveLocalLicense(trimmedKey, result.email);
        safeResolve(true);
        licenseWin.close();
      } else if (result.networkError && saveLocalLicense(trimmedKey, '', { offlineActivated: true, offlineReason: result.reason })) {
        licenseWin.webContents.send('license-status', 'License server could not be reached. Saved offline activation on this PC.');
        safeResolve(true);
        licenseWin.close();
      } else {
        licenseWin.webContents.send('license-error', result.reason || 'Invalid license key.');
        const retryHandler = async (_ev, retryKey) => {
          const rk = (retryKey || '').trim();
          if (!rk) {
            licenseWin.webContents.send('license-error', 'Please enter a license key.');
            ipcMain.once('license-submit', retryHandler);
            return;
          }
          licenseWin.webContents.send('license-status', 'Verifying...');
          const r2 = await verifyWithPayhip(rk);
          if (r2.valid) {
            await incrementPayhipUsage(rk);
            saveLocalLicense(rk, r2.email);
            safeResolve(true);
            licenseWin.close();
          } else if (r2.networkError && saveLocalLicense(rk, '', { offlineActivated: true, offlineReason: r2.reason })) {
            licenseWin.webContents.send('license-status', 'License server could not be reached. Saved offline activation on this PC.');
            safeResolve(true);
            licenseWin.close();
          } else {
            licenseWin.webContents.send('license-error', r2.reason || 'Invalid license key.');
            ipcMain.once('license-submit', retryHandler);
          }
        };
        ipcMain.once('license-submit', retryHandler);
      }
    });

    ipcMain.once('license-buy', () => {
      shell.openExternal('https://payhip.com/b/AHgpV');
    });

    const bypassHandler = (_e, code) => {
      const trimmed = typeof code === 'string' ? code : '';
      if (verifyBypassCode(trimmed)) {
        const wrote = writeBypassFlag();
        debugLog(`[License] Developer bypass code accepted (flag write ok=${wrote})`);
        licenseWin.webContents.send('bypass-result', { ok: true });
        safeResolve(true);
        try { licenseWin.close(); } catch (_) {}
      } else {
        debugLog('[License] Developer bypass code rejected');
        licenseWin.webContents.send('bypass-result', { ok: false });
        ipcMain.once('license-bypass-submit', bypassHandler);
      }
    };
    ipcMain.once('license-bypass-submit', bypassHandler);

    ipcMain.once('license-quit', () => {
      safeResolve(false);
      licenseWin.close();
    });

    licenseWin.on('closed', () => {
      debugLog('[Dialog] License window closed event fired');
      ipcMain.removeAllListeners('license-submit');
      ipcMain.removeAllListeners('license-quit');
      ipcMain.removeAllListeners('license-buy');
      ipcMain.removeAllListeners('license-bypass-submit');
      safeResolve(false);
    });

    licenseWin.loadFile(path.join(__dirname, 'license.html'));
  });
}

async function checkLicenseAndActivate() {
  if (hasBypassFlag()) {
    debugLog('[License] Developer bypass flag present - activation gate skipped');
    return true;
  }

  if (isContributorTestBuild()) {
    debugLog('[License] Contributor test build detected - activation gate bypassed for this package only');
    return true;
  }

  const local = readLocalLicense();
  if (local) {
    console.log(`[License] Valid local activation found (key: ${local.licenseKey.substring(0, 5)}...)`);
    const lastVerified = new Date(local.lastVerified);
    const daysSince = (Date.now() - lastVerified.getTime()) / (1000 * 60 * 60 * 24);
    if (daysSince > 7) {
      console.log('[License] Re-verifying with Payhip (last check was', Math.round(daysSince), 'days ago)');
      const result = await verifyWithPayhip(local.licenseKey);
      if (result.valid) {
        saveLocalLicense(local.licenseKey, local.email);
        return true;
      } else if (result.networkError) {
        console.log('[License] Re-verification skipped (network error) — keeping local license:', result.reason);
        return true;
      } else {
        console.log('[License] Re-verification failed (server rejected) - clearing local license');
        try { fs.unlinkSync(LICENSE_FILE); } catch (_) {}
      }
    } else {
      return true;
    }
  }

  if (hasActiveActivationGrace()) {
    debugLog('[License] No valid activation found, but activation grace is still active');
    return 'grace';
  }

  debugLog('[License] No valid activation found, showing license dialog');
  const activated = await showLicenseDialog();
  debugLog(`[License] showLicenseDialog returned: ${activated}`);
  return activated === true || activated === 'grace' ? activated : false;
}

// ===== IPC: Direct filesystem browsing (bypasses server entirely) =====
// Native pickers use fixed channels and fixed filters. The renderer may suggest
// only a source kind and a starting directory; it can never supply arbitrary
// Electron dialog options or use these handlers from another app window.
const SOURCE_PAINT_EXTENSIONS = Object.freeze({
  flat: Object.freeze(['tga', 'png', 'jpg', 'jpeg', 'bmp']),
  layered: Object.freeze(['psd', 'ora', 'xcf']),
  all: Object.freeze(['tga', 'png', 'jpg', 'jpeg', 'bmp', 'psd', 'ora', 'xcf']),
});

function requireTrustedPaintBoothRenderer(event) {
  if (!mainWindow || mainWindow.isDestroyed() || !event || event.sender !== mainWindow.webContents) {
    throw new Error('Native picker request did not come from the Paint Booth window.');
  }
  try {
    const senderUrl = String((event.senderFrame && event.senderFrame.url) || event.sender.getURL() || '');
    const parsed = new URL(senderUrl);
    if (parsed.protocol === 'http:'
        && parsed.hostname === '127.0.0.1'
        && parsed.port === String(serverPort)) {
      return;
    }
  } catch (_) {}
  throw new Error('Untrusted native picker request blocked.');
}

function nativeDialogDefaultDirectory(rawPath) {
  if (typeof rawPath !== 'string') return undefined;
  const candidate = rawPath.trim();
  if (!candidate || candidate.length > 4096 || candidate.includes('\0')) return undefined;
  try {
    const resolved = path.resolve(candidate);
    if (!fs.existsSync(resolved)) return undefined;
    const stat = fs.statSync(resolved);
    if (stat.isDirectory()) return resolved;
    if (stat.isFile()) return path.dirname(resolved);
  } catch (_) {}
  return undefined;
}

function suggestedIRacingPaintDirectory() {
  const home = os.homedir();
  const candidates = [
    path.join(app.getPath('documents'), 'iRacing', 'paint'),
    path.join(home, 'Documents', 'iRacing', 'paint'),
    path.join(home, 'OneDrive', 'Documents', 'iRacing', 'paint'),
  ];
  try {
    for (const entry of fs.readdirSync(home, { withFileTypes: true })) {
      if (entry.isDirectory() && (entry.name.startsWith('OneDrive -') || entry.name.startsWith('OneDrive-'))) {
        candidates.push(path.join(home, entry.name, 'Documents', 'iRacing', 'paint'));
      }
    }
  } catch (_) {}
  return candidates.find((candidate) => {
    try { return fs.existsSync(candidate) && fs.statSync(candidate).isDirectory(); } catch (_) { return false; }
  });
}

ipcMain.handle('select-source-paint', async (event, request = {}) => {
  requireTrustedPaintBoothRenderer(event);
  const kind = Object.prototype.hasOwnProperty.call(SOURCE_PAINT_EXTENSIONS, request && request.kind)
    ? request.kind
    : 'flat';
  const extensions = SOURCE_PAINT_EXTENSIONS[kind];
  const options = {
    title: kind === 'layered' ? 'Open Layered Paint' : 'Choose a Source Paint',
    properties: ['openFile'],
    filters: [{
      name: kind === 'layered' ? 'Layered paints' : (kind === 'all' ? 'Paint sources' : 'Flat paints'),
      extensions,
    }],
  };
  const defaultPath = nativeDialogDefaultDirectory(request && request.defaultPath);
  if (defaultPath) options.defaultPath = defaultPath;

  const result = await dialog.showOpenDialog(mainWindow, options);
  if (result.canceled || !result.filePaths || result.filePaths.length !== 1) return null;
  const selected = path.resolve(result.filePaths[0]);
  const selectedExtension = path.extname(selected).slice(1).toLowerCase();
  if (!extensions.includes(selectedExtension)
      || !fs.existsSync(selected)
      || !fs.statSync(selected).isFile()) {
    throw new Error('The selected paint is not a supported source file.');
  }
  return selected;
});

ipcMain.handle('select-iracing-car-folder', async (event, request = {}) => {
  requireTrustedPaintBoothRenderer(event);
  const options = {
    title: 'Choose your iRacing Car Folder',
    properties: ['openDirectory', 'createDirectory'],
  };
  const defaultPath = nativeDialogDefaultDirectory(request && request.defaultPath)
    || suggestedIRacingPaintDirectory();
  if (defaultPath) options.defaultPath = defaultPath;

  const result = await dialog.showOpenDialog(mainWindow, options);
  if (result.canceled || !result.filePaths || result.filePaths.length !== 1) return null;
  const selected = path.resolve(result.filePaths[0]);
  if (!fs.existsSync(selected) || !fs.statSync(selected).isDirectory()) {
    throw new Error('The selected iRacing destination is not a folder.');
  }
  return selected;
});

ipcMain.handle('list-dir', async (_event, dirPath, filter) => {
  try {
    if (!dirPath) return null;
    const resolved = path.resolve(dirPath);
    if (!fs.existsSync(resolved) || !fs.statSync(resolved).isDirectory()) {
      return { error: 'Not a directory: ' + resolved };
    }
    const entries = fs.readdirSync(resolved, { withFileTypes: true });
    const folders = [];
    const files = [];
    const MAX_FILES = 200;
    let totalFiles = 0;
    const isLarge = entries.length > 300;

    // [T27 / 8.0.5 HOTFIX 2026-07-25] The layered-file picker sends a COMMA LIST
    // ('.psd,.ora,.xcf'). This handler used to do
    //     lname.endsWith(filter.toLowerCase())
    // which tested every filename against the whole literal string
    // ".psd,.ora,.xcf" — a suffix no real file can have — so the installed app
    // hid EVERY PSD, ORA and XCF. It shipped in 8.0.4 because verification ran
    // in the browser, which uses the server route (file_picker_routes.py), and
    // that one already splits the list into a tuple for str.endswith(). The
    // packaged Electron IPC path was never exercised.
    //
    // Normalise to a suffix ARRAY so single-extension filters ('.tga'), the
    // comma list, odd whitespace, and the empty/show-all case all behave.
    // Note the empty-list case deliberately shows everything rather than
    // hiding everything — a malformed filter must never blank the picker again.
    const allowedSuffixes = String(filter || '')
      .split(',')
      .map(v => v.trim().toLowerCase())
      .filter(Boolean);

    for (const entry of entries) {
      if (entry.name.startsWith('.')) continue;
      if (entry.isDirectory()) {
        folders.push({
          name: entry.name,
          path: path.join(resolved, entry.name).replace(/\\/g, '/'),
          type: 'folder'
        });
      } else {
        if (isLarge) continue;
        const lname = entry.name.toLowerCase();
        if (allowedSuffixes.length && !allowedSuffixes.some(sfx => lname.endsWith(sfx))) continue;
        totalFiles++;
        if (files.length < MAX_FILES) {
          let size = 0;
          try { size = fs.statSync(path.join(resolved, entry.name)).size; } catch (_) {}
          files.push({
            name: entry.name,
            path: path.join(resolved, entry.name).replace(/\\/g, '/'),
            type: 'file',
            size,
            size_human: size > 0 ? Math.round(size / 1024) + ' KB' : '0'
          });
        }
      }
    }

    folders.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
    files.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));

    const parentDir = path.dirname(resolved);
    const parentPath = parentDir !== resolved ? parentDir.replace(/\\/g, '/') : '';

    return {
      path: resolved.replace(/\\/g, '/'),
      parent: parentPath,
      items: folders.concat(files),
      total_folders: folders.length,
      total_files: totalFiles,
      hidden_files: isLarge ? -1 : totalFiles - files.length,
      large_dir: isLarge,
      entry_count: entries.length,
    };
  } catch (err) {
    return { error: err.message };
  }
});

ipcMain.handle('show-folder-dialog', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory'],
    title: 'Select PS Export Folder',
  });
  if (result.canceled || !result.filePaths || result.filePaths.length === 0) return null;
  return result.filePaths[0].replace(/\\/g, '/');
});

ipcMain.handle('get-quick-navs', async () => {
  const drives = [];
  for (const letter of 'CDEFGHIJKLMNOPQRSTUVWXYZ') {
    const drive = letter + ':/';
    if (fs.existsSync(drive)) drives.push({ name: letter + ':', path: drive, type: 'drive' });
  }
  const quick_navs = [];

  const home = os.homedir();
  const iracingCandidates = [
    path.join(home, 'Documents', 'iRacing', 'paint'),
    path.join(home, 'OneDrive', 'Documents', 'iRacing', 'paint'),
  ];

  try {
    const homeEntries = fs.readdirSync(home, { withFileTypes: true });
    for (const entry of homeEntries) {
      if (entry.isDirectory() && (entry.name.startsWith('OneDrive -') || entry.name.startsWith('OneDrive-'))) {
        iracingCandidates.push(path.join(home, entry.name, 'Documents', 'iRacing', 'paint'));
      }
    }
  } catch (_) {}

  if (process.env.USERPROFILE && process.env.USERPROFILE !== home) {
    iracingCandidates.push(path.join(process.env.USERPROFILE, 'Documents', 'iRacing', 'paint'));
  }

  let iracingFound = false;
  for (const candidate of iracingCandidates) {
    try {
      if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
        quick_navs.push({ name: 'iRacing Paint Folder', path: candidate.replace(/\\/g, '/'), type: 'shortcut' });
        console.log(`[QuickNav] iRacing paint folder found: ${candidate}`);
        iracingFound = true;
        break;
      }
    } catch (_) {}
  }
  if (!iracingFound) {
    console.log('[QuickNav] iRacing paint folder not found in any standard location');
  }

  return { drives, quick_navs };
});

// ----- IMPROVEMENT #38: Server port available to renderer over IPC -----
ipcMain.handle('get-server-port', () => serverPort);

// SHOKK FORGE final handoff: validate a ready job output in the main process,
// then call the Paint Booth's existing importer rather than duplicating PSD parsing.
ipcMain.handle('forge-import-psd', async (_event, requestedPath) => {
  if (!mainWindow || mainWindow.isDestroyed()) throw new Error('Paint Booth window is unavailable');
  const resolved = path.resolve(String(requestedPath || ''));
  const forgeRoot = path.resolve(getServerDir(), 'output', 'forge_jobs');
  const insideForgeRoot = resolved === forgeRoot || resolved.startsWith(forgeRoot + path.sep);
  if (!insideForgeRoot) throw new Error('Forge PSD path is outside the local jobs root');
  if (path.extname(resolved).toLowerCase() !== '.psd') throw new Error('Forge handoff requires a PSD file');
  if (!fs.existsSync(resolved) || !fs.statSync(resolved).isFile()) throw new Error('Forge PSD output was not found');
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
  const literal = JSON.stringify(resolved);
  return mainWindow.webContents.executeJavaScript(`(async () => {
    if (typeof window.importPSDFromPath !== 'function') throw new Error('Paint Booth PSD importer is not ready');
    await window.importPSDFromPath(${literal});
    return { success: true };
  })()`, true);
});

async function collectGpuStatus() {
  const featureStatus = (() => {
    try { return app.getGPUFeatureStatus ? app.getGPUFeatureStatus() : null; } catch (e) { return { error: e.message }; }
  })();
  const readInfo = async (kind) => {
    try {
      return app.getGPUInfo ? await app.getGPUInfo(kind) : null;
    } catch (e) {
      return { error: e.message };
    }
  };
  const [basic, complete] = await Promise.all([readInfo('basic'), readInfo('complete')]);
  return {
    electron: process.versions.electron,
    chromium: process.versions.chrome,
    disabledByFlag: gpuDisabledByFlag,
    disableFlagPath: GPU_DISABLE_FLAG,
    launchSwitches: {
      useAngle: 'd3d11',
      forceHighPerformanceGpu: true,
      ignoreGpuBlocklist: true,
      gpuRasterization: true,
      accelerated2dCanvas: true,
      webgl: true,
      zeroCopy: true,
      features: 'CanvasOopRasterization,UseSkiaRenderer'
    },
    featureStatus,
    basic,
    complete
  };
}

ipcMain.handle('gpu-status', async () => collectGpuStatus());

// ----- IMPROVEMENT #13/26: About dialog + external links -----
ipcMain.handle('app-version', () => app.getVersion());
ipcMain.handle('open-external', async (_e, url) => {
  if (!/^https?:\/\//i.test(String(url || ''))) return false;
  await shell.openExternal(url);
  return true;
});

// ----- Auto-updater: renderer-driven Download / Install (in-app banner) -----
ipcMain.handle('start-update-download', () => {
  try { return autoUpdater.downloadUpdate(); } catch (e) { return { error: String(e) }; }
});
ipcMain.handle('install-update', () => {
  try { autoUpdater.quitAndInstall(false, true); } catch (e) { return { error: String(e) }; }
});

ipcMain.handle('show-about', () => {
  showAboutDialog();
  return true;
});

ipcMain.handle('show-error', (_e, title, message) => {
  dialog.showErrorBox(String(title || 'Error'), String(message || ''));
  return true;
});

// ----- IMPROVEMENT #14: Renderer can declare unsaved work -----
ipcMain.handle('set-unsaved-state', (_e, hasUnsaved) => {
  unsavedWork = !!hasUnsaved;
  if (mainWindow) mainWindow.setDocumentEdited(unsavedWork);
  return true;
});

// ----- IMPROVEMENT #29: Recent files / Jump List -----
function readRecentFiles() {
  try {
    if (!fs.existsSync(RECENT_FILES_FILE)) return [];
    const list = JSON.parse(fs.readFileSync(RECENT_FILES_FILE, 'utf8'));
    return Array.isArray(list) ? list.slice(0, 10) : [];
  } catch (_) { return []; }
}
function writeRecentFiles(list) {
  try { fs.writeFileSync(RECENT_FILES_FILE, JSON.stringify(list.slice(0, 10), null, 2), 'utf8'); } catch (_) {}
}
function refreshJumpList() {
  if (process.platform !== 'win32') return;
  const recent = readRecentFiles();
  try {
    app.setJumpList([
      {
        type: 'custom',
        name: 'Recent Paints',
        items: recent.map((p) => ({
          type: 'task',
          title: path.basename(p),
          program: process.execPath,
          args: `"${p}"`,
          description: p,
        })),
      },
      { type: 'recent' },
    ]);
  } catch (e) {
    debugLog(`[JumpList] setJumpList failed: ${e.message}`);
  }
}
ipcMain.handle('get-recent-files', () => readRecentFiles());
ipcMain.handle('add-recent-file', (_e, filePath) => {
  if (!filePath) return false;
  const list = readRecentFiles().filter((p) => p !== filePath);
  list.unshift(filePath);
  writeRecentFiles(list);
  try { app.addRecentDocument(filePath); } catch (_) {}
  refreshJumpList();
  return true;
});

// ----- IMPROVEMENT #6/7/8: Renderer-driven dev shortcuts -----
ipcMain.handle('request-reload', () => {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.reload();
  return true;
});
ipcMain.handle('request-hard-reload', async () => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    try { await mainWindow.webContents.session.clearCache(); } catch (_) {}
    mainWindow.webContents.reloadIgnoringCache();
  }
  return true;
});
ipcMain.handle('request-toggle-devtools', () => {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.toggleDevTools();
  return true;
});

// 2026-06-08: real restart so downloaded Finish Packs load (page reload alone leaves the old server running)
// 2026-06-17 — TOTAL FRESH START: this is the single path every in-app
// "Fresh Start" / "Restart now" funnels through (preload.js -> restartApp /
// spbRestartApp). The bug it fixes: an ORPHANED old backend kept holding
// :59876 after relaunch, so the new instance reconnected to STALE engine code.
// We now stop only the tracked child. The relaunched instance verifies any
// remaining :59876 listener by health identity + owning PID/process ancestry
// before it can reclaim a true orphan; unknown holders fail closed.
ipcMain.on('spb-restart-app', () => {
  try {
    // The tracked child is authoritative and safe to stop. Never sweep a port
    // or image name here: the new instance performs verified orphan recovery.
    gracefulShutdown('spb-restart-app');
  } catch (_) {}
  // app.relaunch() must be called BEFORE app.exit().
  app.relaunch();
  app.exit(0);
});

// ----- IMPROVEMENT #20/39: Renderer log forwarding -----
ipcMain.handle('log-renderer', (_e, level, message) => {
  debugLog(`[Renderer:${level}] ${message}`);
  return true;
});

// ----- Experimental iRacing native preview bridge for SHOKKER Finish Viewer -----
ipcMain.handle('iracing-native-status', async () => {
  return sendIracingNativeBridgeCommandAuto('status', {}, 12000);
});

ipcMain.handle('iracing-native-attach', async (_e, payload = {}) => {
  const win = getIracingBridgeTargetWindow();
  const hwnd = getNativeWindowHandleInt(win);
  hookIracingNotifyMessages(win);
  return sendIracingNativeBridgeCommandAuto('attach', Object.assign({}, payload, { hwnd }), 12000);
});

ipcMain.handle('iracing-native-create', async (_e, payload = {}) => {
  const win = getIracingBridgeTargetWindow();
  const hwnd = getNativeWindowHandleInt(win);
  hookIracingNotifyMessages(win);
  const rect = nativeBridgeScreenRect(win, payload);
  return sendIracingNativeBridgeCommandAuto('create', Object.assign({}, payload, rect, { hwnd }), 15000);
});

ipcMain.handle('iracing-native-resize', async (_e, payload = {}) => {
  const win = getIracingBridgeTargetWindow();
  const rect = nativeBridgeScreenRect(win, payload);
  return sendIracingNativeBridgeCommandAuto('resize', Object.assign({}, payload, rect), 8000);
});

ipcMain.handle('iracing-native-load', async (_e, payload = {}) => {
  return sendIracingNativeBridgeCommandAuto('load', payload, 20000);
});

ipcMain.handle('iracing-native-paint', async (_e, payload = {}) => {
  return sendIracingNativeBridgeCommandAuto('paint', payload, 12000);
});

ipcMain.handle('iracing-native-shutdown', async () => {
  const result = await sendIracingNativeBridgeCommandAuto('shutdown', {}, 8000);
  stopIracingNativeBridgeProcess('renderer shutdown request');
  return result;
});

// ----- IMPROVEMENT #21 (renderer side): crash report channel -----
ipcMain.on('renderer-crash-report', (_e, payload) => {
  try { debugLog(`[Renderer:CRASH] ${JSON.stringify(payload).slice(0, 2000)}`); } catch (_) {}
});

ipcMain.on('renderer-ready', () => {
  debugLog('[Renderer] DOMContentLoaded fired');
  rendererReadyForDeepLinks = true;
  while (pendingDeepLinks.length && mainWindow && !mainWindow.isDestroyed()) {
    const nextUrl = pendingDeepLinks.shift();
    try { mainWindow.webContents.send('deep-link', nextUrl); } catch (_) { pendingDeepLinks.unshift(nextUrl); break; }
  }
});

// ===== STABLE SERVER ORIGIN / VERIFIED ORPHAN RECOVERY (2026-08-22) =====
// Production always owns 127.0.0.1:59876. A busy port is reclaimed only when
// /build-check identifies this exact SPB server, its reported PID is the sole
// listener, its process command is an SPB server child, and its parent is gone.
// Anything ambiguous remains untouched and produces a visible startup error.
const SPB_BUILD_IDENTITY = 'Shokker Engine V5 - Modular Architecture';

function getPidsOnPort(port) {
  if (process.platform !== 'win32') return [];
  const myPid = process.pid;
  const found = new Set();
  try {
    const { execSync } = require('child_process');
    const out = execSync(`netstat -ano | findstr :${port} | findstr LISTENING`,
      { encoding: 'utf-8', windowsHide: true, timeout: 5000 });
    for (const line of out.trim().split('\n')) {
      const parts = line.trim().split(/\s+/);
      const local = parts[1] || '';
      if (!local.endsWith(`:${port}`)) continue;
      const pid = parseInt(parts[parts.length - 1], 10);
      if (Number.isFinite(pid) && pid !== myPid && pid > 4) found.add(pid);
    }
  } catch (_) {}
  return Array.from(found);
}

function _sameStableOriginPath(left, right) {
  const normalize = (value) => String(value || '')
    .replace(/\//g, '\\')
    .replace(/\\+$/, '')
    .toLowerCase();
  return !!normalize(left) && normalize(left) === normalize(right);
}

function _classifyStablePortHolder(input) {
  const blocked = (reason) => ({ kind: 'blocked', reason });
  const port = Number(input && input.port);
  const pids = Array.from(new Set(((input && input.pids) || [])
    .map((pid) => Number(pid)).filter((pid) => Number.isInteger(pid) && pid > 4)));
  if (pids.length === 0) return blocked('the listening PID could not be identified');
  if (pids.length !== 1) return blocked('multiple processes report ownership of the stable port');

  const identity = input && input.identity;
  if (!identity || identity.status !== 'running' || identity.engine !== SPB_BUILD_IDENTITY) {
    return blocked('the listener did not return the expected SPB build identity');
  }
  if (Number(identity.port) !== port || !Number.isInteger(Number(identity.pid))) {
    return blocked('the SPB health identity reported a different port or invalid PID');
  }
  const identityPid = Number(identity.pid);
  if (pids[0] !== identityPid) {
    return blocked('the health PID does not own the listening socket');
  }
  if (!_sameStableOriginPath(identity.server_dir, input && input.expectedServerDir)) {
    return blocked('the listener belongs to a different SPB server directory');
  }

  const info = input && input.processInfo;
  if (!info || Number(info.pid) !== identityPid) {
    return blocked('the owning process metadata could not be verified');
  }
  const commandLine = String(info.commandLine || '');
  const executablePath = String(info.executablePath || '');
  const runsServerScript = /(?:^|[\\/"'\s])server_v5\.py(?:$|["'\s])/i.test(commandLine);
  const executableName = executablePath.replace(/\//g, '\\').split('\\').pop().toLowerCase();
  const expectedDir = String(input.expectedServerDir || '').replace(/\//g, '\\').replace(/\\+$/, '').toLowerCase();
  const executableLower = executablePath.replace(/\//g, '\\').toLowerCase();
  const knownBundledExe = (executableName === 'shokker-paint-booth-v5.exe' || executableName === 'shokker-server.exe')
    && executableLower.startsWith(expectedDir + '\\');
  if (!runsServerScript && !knownBundledExe) {
    return blocked('the owning process command is not an SPB server child');
  }
  if (info.parentAlive !== false) {
    return blocked('the verified SPB server still has a live parent and is not an orphan');
  }
  return { kind: 'verified_spb_orphan', pid: identityPid };
}

function probeSpbServerIdentity(port, opts = {}) {
  const httpClient = opts.httpClient || http;
  const timeoutMs = Number(opts.timeoutMs) || 1200;
  return new Promise((resolve) => {
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      resolve(value || null);
    };
    let request;
    try {
      request = httpClient.get({
        hostname: '127.0.0.1',
        port,
        path: '/build-check',
        headers: { 'X-Shokker-Internal': '1' },
      }, (response) => {
        let body = '';
        response.setEncoding('utf8');
        response.on('data', (chunk) => {
          body += chunk;
          if (body.length > 65536) {
            try { request.destroy(); } catch (_) {}
            finish(null);
          }
        });
        response.on('end', () => {
          if (response.statusCode !== 200 || body.length > 65536) return finish(null);
          try { finish(JSON.parse(body)); } catch (_) { finish(null); }
        });
      });
      request.setTimeout(timeoutMs, () => {
        try { request.destroy(); } catch (_) {}
        finish(null);
      });
      request.once('error', () => finish(null));
    } catch (_) {
      finish(null);
    }
  });
}

function getWindowsProcessInfo(pid) {
  const safePid = Number(pid);
  if (process.platform !== 'win32' || !Number.isInteger(safePid) || safePid <= 4) return null;
  try {
    const { execFileSync } = require('child_process');
    const script = [
      `$p=Get-CimInstance Win32_Process -Filter "ProcessId = ${safePid}" -ErrorAction SilentlyContinue;`,
      'if($null -eq $p){exit 3};',
      '$pa=$null -ne (Get-Process -Id $p.ParentProcessId -ErrorAction SilentlyContinue);',
      '[pscustomobject]@{pid=[int]$p.ProcessId;parentPid=[int]$p.ParentProcessId;parentAlive=[bool]$pa;',
      'creationDate=[string]$p.CreationDate;executablePath=[string]$p.ExecutablePath;',
      'commandLine=[string]$p.CommandLine}|ConvertTo-Json -Compress',
    ].join('');
    const raw = execFileSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', script],
      { encoding: 'utf8', windowsHide: true, timeout: 5000 });
    return JSON.parse(raw);
  } catch (_) {
    return null;
  }
}

function _killVerifiedSpbPid(pid) {
  const safePid = Number(pid);
  if (process.platform !== 'win32' || !Number.isInteger(safePid) || safePid <= 4 || safePid === process.pid) {
    throw new Error('Refused invalid verified-orphan PID');
  }
  const { execFileSync } = require('child_process');
  execFileSync('taskkill.exe', ['/F', '/PID', String(safePid), '/T'],
    { windowsHide: true, timeout: 5000, stdio: 'ignore' });
}

async function _waitForStablePortRelease(port, timeoutMs, deps = {}) {
  const checkFree = deps.isPortFree || isPortFree;
  const delay = deps.delay || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  const deadline = Date.now() + (Number(timeoutMs) || 4000);
  do {
    if (await checkFree(port)) return true;
    await delay(100);
  } while (Date.now() < deadline);
  return false;
}

async function ensureStableServerPortAvailable(port, deps = {}) {
  const checkFree = deps.isPortFree || isPortFree;
  if (await checkFree(port)) return { port, reclaimed: false };

  const listPids = deps.getPidsOnPort || getPidsOnPort;
  const probeIdentity = deps.probeIdentity || probeSpbServerIdentity;
  const readProcess = deps.getProcessInfo || getWindowsProcessInfo;
  const expectedServerDir = (deps.getServerDir || getServerDir)();
  let pids = [];
  try { pids = listPids(port); } catch (_) {}
  const identity = await probeIdentity(port);
  const identityPid = identity && Number(identity.pid);
  const processInfo = Number.isInteger(identityPid) ? readProcess(identityPid) : null;
  const decision = _classifyStablePortHolder({
    port,
    expectedServerDir,
    pids,
    identity,
    processInfo,
  });
  if (decision.kind !== 'verified_spb_orphan') {
    throw new Error(
      `Stable SPB origin http://127.0.0.1:${port} is occupied, but SPB will not stop that process: ${decision.reason}. ` +
      'Close the application using this port and start SPB again. SPB will not switch ports because that would hide saved local data.'
    );
  }

  // Close the inspect-to-kill race: repeat the socket, endpoint, and process
  // checks immediately before taskkill. If ownership moved, fail without
  // touching either the old PID or its replacement.
  let confirmedPids = [];
  try { confirmedPids = listPids(port); } catch (_) {}
  const confirmedIdentity = await probeIdentity(port);
  const confirmedPid = confirmedIdentity && Number(confirmedIdentity.pid);
  const confirmedInfo = Number.isInteger(confirmedPid) ? readProcess(confirmedPid) : null;
  const confirmed = _classifyStablePortHolder({
    port,
    expectedServerDir,
    pids: confirmedPids,
    identity: confirmedIdentity,
    processInfo: confirmedInfo,
  });
  const creationChanged = processInfo && processInfo.creationDate && confirmedInfo && confirmedInfo.creationDate
    && String(processInfo.creationDate) !== String(confirmedInfo.creationDate);
  if (confirmed.kind !== 'verified_spb_orphan' || confirmed.pid !== decision.pid || creationChanged) {
    throw new Error(
      `Stable SPB origin http://127.0.0.1:${port} changed ownership during verification; no process was stopped`
    );
  }

  debugLog(`[StableOrigin] Reclaiming verified orphaned SPB PID ${decision.pid} on :${port}`);
  const killPid = deps.killPid || _killVerifiedSpbPid;
  try {
    await killPid(decision.pid);
  } catch (error) {
    throw new Error(`Verified orphaned SPB PID ${decision.pid} could not be stopped: ${error.message}`);
  }
  const waitForRelease = deps.waitForPortFree || _waitForStablePortRelease;
  if (!(await waitForRelease(port, 4000, { isPortFree: checkFree, delay: deps.delay }))) {
    throw new Error(`Verified orphaned SPB PID ${decision.pid} stopped, but stable port ${port} did not release`);
  }
  return { port, reclaimed: true, pid: decision.pid };
}

// ===== BUNDLED PYTHON PATH (preserved) =====
function getBundledPythonPath() {
  const candidates = [
    path.join(process.resourcesPath, 'server', 'python', 'python.exe'),
    path.join(__dirname, 'server', 'python', 'python.exe'),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) {
      debugLog(`[Server] Found bundled Python at: ${p}`);
      return p;
    }
  }
  return null;
}

function getServerDir() {
  const packaged = path.join(process.resourcesPath, 'server');
  if (fs.existsSync(path.join(packaged, 'server_v5.py'))) return packaged;
  const dev = path.join(__dirname, 'server');
  if (fs.existsSync(path.join(dev, 'server_v5.py'))) return dev;
  return path.join(__dirname, 'server');
}

function getIracingNativeBridgeScriptPath() {
  const packaged = path.join(process.resourcesPath, 'server', 'tools', 'iracing_native_bridge.py');
  if (fs.existsSync(packaged)) return packaged;
  return path.join(__dirname, 'server', 'tools', 'iracing_native_bridge.py');
}

function getNativeWindowHandleInt(win) {
  if (!win || win.isDestroyed()) throw new Error('No active Electron window is available.');
  const handle = win.getNativeWindowHandle();
  return handle.readUInt32LE(0);
}

function getIracingBridgeTargetWindow() {
  if (iracingNativeTargetWindow && !iracingNativeTargetWindow.isDestroyed()) return iracingNativeTargetWindow;
  if (finishViewerWindow && !finishViewerWindow.isDestroyed()) return finishViewerWindow;
  if (mainWindow && !mainWindow.isDestroyed()) return mainWindow;
  throw new Error('No SHOKKER window is available for the iRacing native bridge.');
}

function normalizeBridgeRect(payload) {
  const rect = payload && typeof payload === 'object' ? payload : {};
  const num = (value, fallback) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? Math.round(parsed) : fallback;
  };
  return {
    x: Math.max(0, num(rect.x, 24)),
    y: Math.max(0, num(rect.y, 90)),
    width: Math.max(100, num(rect.width, 900)),
    height: Math.max(100, num(rect.height, 620)),
  };
}

function nativeBridgeScreenRect(win, payload) {
  if (iracingNativeHostWindow && win === iracingNativeHostWindow && !win.isDestroyed()) {
    const bounds = win.getContentBounds();
    try {
      return screen.dipToScreenRect(win, { x: 0, y: 0, width: bounds.width, height: bounds.height });
    } catch (_) {
      return bounds;
    }
  }
  const rect = normalizeBridgeRect(payload);
  try {
    return screen.dipToScreenRect(win, rect);
  } catch (_) {
    return rect;
  }
}

function closeIracingNativeHostWindow() {
  if (!iracingNativeHostWindow) return;
  const host = iracingNativeHostWindow;
  iracingNativeHostWindow = null;
  if (iracingNativeTargetWindow === host) iracingNativeTargetWindow = null;
  try {
    if (!host.isDestroyed()) host.close();
  } catch (_) {}
}

function ensureIracingNativeHostWindow(data = {}) {
  if (iracingNativeHostWindow && !iracingNativeHostWindow.isDestroyed()) {
    iracingNativeHostWindow.show();
    iracingNativeHostWindow.focus();
    return iracingNativeHostWindow;
  }

  const parentBounds = finishViewerWindow && !finishViewerWindow.isDestroyed()
    ? finishViewerWindow.getBounds()
    : (mainWindow && !mainWindow.isDestroyed() ? mainWindow.getBounds() : screen.getPrimaryDisplay().workArea);
  const requested = normalizeBridgeRect(data);
  const width = Math.max(900, Math.min(parentBounds.width || 1280, requested.width || 1100));
  const height = Math.max(560, Math.min(parentBounds.height || 780, requested.height || 680));
  const x = Math.max(0, Math.round((parentBounds.x || 0) + Math.max(24, ((parentBounds.width || width) - width) / 2)));
  const y = Math.max(0, Math.round((parentBounds.y || 0) + Math.max(44, ((parentBounds.height || height) - height) / 2)));

  iracingNativeHostWindow = new BrowserWindow({
    width,
    height,
    x,
    y,
    minWidth: 900,
    minHeight: 560,
    title: 'iRacing',
    backgroundColor: '#000000',
    frame: false,
    fullscreenable: false,
    transparent: false,
    show: false,
    opacity: 1,
    autoHideMenuBar: true,
    titleBarStyle: 'hidden',
    titleBarOverlay: { height: 31, color: '#05080d', symbolColor: '#e6edf6' },
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      spellcheck: false,
    },
  });
  iracingNativeHostWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(
    '<!doctype html><html><head><meta charset="utf-8"><title>iRacing</title><style>html,body{margin:0;width:100%;height:100%;background:#000;color:#9fb3c8;font:12px Segoe UI,sans-serif;overflow:hidden}.tag{position:absolute;left:12px;top:10px;opacity:.55}</style></head><body><div class="tag">SHOKKER native iRacing preview host</div></body></html>'
  ));
  iracingNativeHostWindow.once('ready-to-show', () => {
    if (iracingNativeHostWindow && !iracingNativeHostWindow.isDestroyed()) iracingNativeHostWindow.show();
  });
  iracingNativeHostWindow.on('closed', () => {
    if (iracingNativeTargetWindow === iracingNativeHostWindow) iracingNativeTargetWindow = null;
    iracingNativeHostWindow = null;
  });
  iracingNativeHostWindow.show();
  iracingNativeHostWindow.focus();
  debugLog(`[iRacingBridge] Created dedicated iRacing-style host window ${x},${y} ${width}x${height}`);
  return iracingNativeHostWindow;
}

function findIracingRootForNativeBridge() {
  const roots = [
    process.env.IRACING_ROOT,
    'C:\\iRacing',
    'D:\\iRacing',
    path.join(process.env.ProgramFiles || 'C:\\Program Files', 'iRacing'),
    path.join(process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)', 'iRacing'),
  ].filter(Boolean);
  for (const root of roots) {
    try {
      if (fs.existsSync(path.join(root, 'ui', 'iRacingViewer.dll'))) return root;
    } catch (_) {}
  }
  return null;
}

function getIracingUiProcessesMain() {
  if (process.platform !== 'win32') return [];
  try {
    const { execFileSync } = require('child_process');
    const out = execFileSync('tasklist', ['/FI', 'IMAGENAME eq iRacingUI.exe', '/FO', 'CSV', '/NH'], {
      encoding: 'utf8',
      windowsHide: true,
      timeout: 3000,
    });
    return out.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).filter((line) => !line.includes('No tasks are running')).map((line) => {
      const parts = line.replace(/^"|"$/g, '').split('","');
      return { name: parts[0] || 'iRacingUI.exe', pid: Number.parseInt(parts[1], 10) || 0 };
    }).filter((row) => row.name.toLowerCase() === 'iracingui.exe');
  } catch (_) {
    return [];
  }
}

function decodeIracingRegistrationChar(raw) {
  if (typeof raw === 'number') return { raw: String.fromCharCode(raw), code: raw, truthy: raw !== 0 };
  if (typeof raw === 'string') {
    const code = raw.length ? raw.charCodeAt(0) : 0;
    return { raw, code, truthy: code !== 0 };
  }
  if (Buffer.isBuffer(raw)) {
    const code = raw.length ? raw[0] : 0;
    return { raw: raw.toString('latin1'), code, truthy: code !== 0 };
  }
  const text = String(raw || '');
  const code = text.length ? text.charCodeAt(0) : 0;
  return { raw: text, code, truthy: code !== 0 };
}

function loadIracingKoffiModule(root) {
  const candidates = [
    'koffi',
    root ? path.join(root, 'ui', 'resources', 'app.asar', 'node_modules', 'koffi') : null,
  ].filter(Boolean);
  const errors = [];
  for (const candidate of candidates) {
    try {
      return { koffi: require(candidate), modulePath: candidate };
    } catch (err) {
      errors.push(`${candidate}: ${err.message}`);
    }
  }
  throw new Error(`Could not load Koffi for iRacing native bridge. ${errors.join(' | ')}`);
}

function createIracingKoffiBridge() {
  if (process.platform !== 'win32') throw new Error('The iRacing native viewer bridge is Windows-only.');
  const root = findIracingRootForNativeBridge();
  if (!root) throw new Error('iRacingViewer.dll was not found in the standard local iRacing folders.');
  const uiDir = path.join(root, 'ui');
  const dllPath = path.join(uiDir, 'iRacingViewer.dll');
  const { koffi, modulePath } = loadIracingKoffiModule(root);
  process.env.PATH = `${uiDir};${root};${process.env.PATH || ''}`;
  let dll = null;
  try {
    dll = koffi.load(dllPath);
  } catch (firstErr) {
    const previousCwd = process.cwd();
    try {
      process.chdir(uiDir);
      dll = koffi.load('iRacingViewer.dll');
    } catch (_) {
      throw firstErr;
    } finally {
      try { process.chdir(previousCwd); } catch (_) {}
    }
  }
  const funcs = {};
  const bind = (name, result, args) => {
    try {
      funcs[name] = dll.func('__stdcall', name, result, args);
    } catch (err) {
      debugLog(`[iRacingKoffi] bind failed ${name}: ${err.message}`);
    }
  };
  bind('iRacingHostRegister', 'bool', ['uint64']);
  bind('iRacingHostDeregister', 'void', []);
  bind('iRacingHostRegisterDemo', 'bool', ['uint64']);
  bind('iRacingHostDeregisterDemo', 'void', []);
  bind('isIRacingUIRegistered', 'char', []);
  bind('isTransparencyEnabled', 'bool', []);
  bind('onNotifyMsgRecv', 'void', ['int']);
  bind('viewerSupportBegin', 'bool', ['uint64']);
  bind('viewerSupportEnd', 'void', []);
  bind('viewerSetPathDetails', 'bool', ['string']);
  bind('viewerSetFrameWindowBGColor', 'void', ['string']);
  bind('viewerCreateView', 'bool', ['int', 'int', 'int', 'int', 'int']);
  bind('viewerDeleteView', 'bool', ['int']);
  bind('viewerRepositionView', 'bool', ['int', 'int', 'int', 'int', 'int']);
  bind('viewerLoadBackgroundObject', 'bool', ['int', 'string', 'string']);
  bind('viewerLoadObject', 'bool', ['int', 'int', 'string', 'string', 'int', 'string', 'string']);
  bind('viewerPaintWheelsDefault', 'bool', ['int']);
  bind('viewerPaintWheelsCustom', 'bool', ['int', 'string', 'int']);
  bind('viewerPaintItem', 'bool', [
    'int', 'int', 'int',
    'string', 'string', 'string', 'string',
    'int', 'bool', 'bool', 'int', 'int',
    'string', 'string', 'string', 'string',
    'int', 'int', 'int', 'bool', 'string', 'bool',
  ]);
  bind('viewerSetDriverHeadType', 'void', ['int', 'int']);

  const bridge = {
    root,
    uiDir,
    dllPath,
    modulePath,
    funcs,
    attachedHwnd: null,
    registrationMode: '',
    viewCreated: false,
    lastCarPath: '',
    status() {
      const payload = {
        bridge: 'electron-koffi',
        root,
        dll: dllPath,
        koffi_module: modulePath,
        loaded: true,
        attached_hwnd: this.attachedHwnd,
        registration_mode: this.registrationMode,
        view_created: this.viewCreated,
        last_car_path: this.lastCarPath,
        native_host_window: iracingNativeHostWindow && !iracingNativeHostWindow.isDestroyed()
          ? Object.assign({ title: iracingNativeHostWindow.getTitle() }, iracingNativeHostWindow.getBounds())
          : null,
        target_window: iracingNativeTargetWindow && !iracingNativeTargetWindow.isDestroyed()
          ? iracingNativeTargetWindow.getTitle()
          : null,
        iracing_ui_processes: getIracingUiProcessesMain(),
        functions: Object.keys(funcs).sort(),
      };
      if (funcs.isTransparencyEnabled) payload.transparency_enabled = Boolean(funcs.isTransparencyEnabled());
      if (funcs.isIRacingUIRegistered) {
        const registration = decodeIracingRegistrationChar(funcs.isIRacingUIRegistered());
        payload.ui_registered_raw = registration.raw;
        payload.ui_registered_code = registration.code;
        payload.ui_registered = registration.truthy;
      }
      return payload;
    },
    attach(data = {}) {
      const bg = String(data.background || '000000').replace(/^#/, '').slice(0, 6) || '000000';
      const transparency = funcs.isTransparencyEnabled ? Boolean(funcs.isTransparencyEnabled()) : false;
      const attempts = [];
      const tryAttachWindow = (label, win, fallbackHwnd = 0) => {
        if (!win || win.isDestroyed()) return { label, hwnd: fallbackHwnd, registered: false, support_begin: false, skipped: true };
        win.show();
        try { win.focus(); } catch (_) {}
        const hwnd = fallbackHwnd || getNativeWindowHandleInt(win);
        const registered = funcs.iRacingHostRegister ? Boolean(funcs.iRacingHostRegister(hwnd)) : false;
        const supportBegin = funcs.viewerSupportBegin ? Boolean(funcs.viewerSupportBegin(hwnd)) : false;
        let registeredDemo = false;
        let supportBeginAfterDemo = false;
        if (!registered && !supportBegin && funcs.iRacingHostRegisterDemo) {
          registeredDemo = Boolean(funcs.iRacingHostRegisterDemo(hwnd));
          supportBeginAfterDemo = funcs.viewerSupportBegin ? Boolean(funcs.viewerSupportBegin(hwnd)) : false;
        }
        const title = typeof win.getTitle === 'function' ? win.getTitle() : '';
        const bounds = typeof win.getBounds === 'function' ? win.getBounds() : null;
        const attempt = {
          label,
          hwnd,
          title,
          registered,
          support_begin: supportBegin,
          registered_demo: registeredDemo,
          support_begin_after_demo: supportBeginAfterDemo,
          bounds,
        };
        attempts.push(attempt);
        if (registered || supportBegin || registeredDemo || supportBeginAfterDemo) {
          this.attachedHwnd = hwnd;
          this.registrationMode = registered || supportBegin ? 'standard' : 'demo';
          iracingNativeTargetWindow = win;
        }
        return attempt;
      };

      const primaryWin = getIracingBridgeTargetWindow();
      const providedHwnd = Number(data.hwnd) || 0;
      let accepted = tryAttachWindow('finish-viewer-window', primaryWin, providedHwnd);
      if (!accepted.registered && !accepted.support_begin) {
        const hostWin = ensureIracingNativeHostWindow(data);
        accepted = tryAttachWindow('dedicated-iracing-host-window', hostWin);
      }
      if (funcs.viewerSetFrameWindowBGColor) funcs.viewerSetFrameWindowBGColor(bg);
      const runningUi = getIracingUiProcessesMain();
      let hint = '';
      const acceptedOk = Boolean(accepted.registered || accepted.support_begin || accepted.registered_demo || accepted.support_begin_after_demo);
      if (!acceptedOk && runningUi.length) {
        hint = 'iRacingUI.exe is already running and may own the only native preview host. Close iRacing UI, then retry Test Bridge.';
      } else if (!acceptedOk) {
        hint = 'Electron/Koffi bridge reached the DLL, but the DLL rejected the standard and demo registration paths for both HWNDs.';
      } else if (accepted.label === 'dedicated-iracing-host-window') {
        hint = 'The DLL accepted a dedicated iRacing-style host window. Next step is embedding or aligning this native host with SHOKKER controls.';
      } else if (accepted.registered_demo || accepted.support_begin_after_demo) {
        hint = 'The DLL accepted the demo host registration path.';
      }
      return {
        bridge: 'electron-koffi',
        hwnd: accepted.hwnd || providedHwnd,
        registered: Boolean(accepted.registered || accepted.registered_demo),
        support_begin: Boolean(accepted.support_begin || accepted.support_begin_after_demo),
        registration_mode: this.registrationMode,
        target: accepted.label,
        attempts,
        transparency_enabled: transparency,
        background: bg,
        iracing_ui_processes: runningUi,
        hint,
      };
    },
    create(data = {}) {
      if (!this.attachedHwnd && data.hwnd) this.attach(data);
      const view = Number(data.view) || 0;
      const x = Math.max(0, Number(data.x) || 0);
      const y = Math.max(0, Number(data.y) || 0);
      const width = Math.max(100, Number(data.width) || 900);
      const height = Math.max(100, Number(data.height) || 620);
      const created = funcs.viewerCreateView ? Boolean(funcs.viewerCreateView(view, x, y, width, height)) : false;
      this.viewCreated = created;
      let backgroundLoaded = false;
      if (created && funcs.viewerLoadBackgroundObject) {
        backgroundLoaded = Boolean(funcs.viewerLoadBackgroundObject(view, 'cars', 'ui_bg.3do'));
      }
      return { bridge: 'electron-koffi', view, created, background_loaded: backgroundLoaded, rect: [x, y, width, height] };
    },
    resize(data = {}) {
      const view = Number(data.view) || 0;
      const x = Math.max(0, Number(data.x) || 0);
      const y = Math.max(0, Number(data.y) || 0);
      const width = Math.max(100, Number(data.width) || 900);
      const height = Math.max(100, Number(data.height) || 620);
      const ok = funcs.viewerRepositionView ? Boolean(funcs.viewerRepositionView(view, x, y, width, height)) : false;
      return { bridge: 'electron-koffi', view, resized: ok, rect: [x, y, width, height] };
    },
    load(data = {}) {
      const view = Number(data.view) || 0;
      const itemType = Number(data.type ?? data.itemType) || 0;
      const rawPath = String(data.objPath || data.carPath || 'cars\\c8rvettegte').replace(/\//g, '\\').replace(/^\\+/, '');
      const carCfg = Number.isFinite(Number(data.carCfg)) ? Number(data.carCfg) : -1;
      const subDir = String(data.carCfgSubDir || '');
      const paintExt = String(data.carCfgCustomPaintExt || '');
      if (itemType !== 0) {
        let objPath = 'cars';
        let objName = 'driver_helmet.3do';
        if (itemType === 1) objName = `driver_body_0${rawPath || 1}_ui_anim.3do`;
        const loaded = funcs.viewerLoadObject ? Boolean(funcs.viewerLoadObject(view, itemType, objPath, objName, carCfg, subDir, paintExt)) : false;
        return { bridge: 'electron-koffi', view, type: itemType, obj_path: objPath, obj_name: objName, loaded, car_cfg: carCfg, car_cfg_sub_dir: subDir, paint_ext: paintExt };
      }
      const candidates = rawPath.toLowerCase().startsWith('cars\\')
        ? [rawPath, rawPath.replace(/^cars\\/, '')]
        : [rawPath, `cars\\${rawPath}`];
      const attempts = [];
      let loaded = false;
      let objPath = candidates[0];
      let objName = `${objPath.split('\\').pop()}_ui.3do`;
      for (const candidate of candidates) {
        objPath = candidate;
        objName = `${candidate.split('\\').pop()}_ui.3do`;
        loaded = funcs.viewerLoadObject ? Boolean(funcs.viewerLoadObject(view, itemType, objPath, objName, carCfg, subDir, paintExt)) : false;
        attempts.push({ obj_path: objPath, obj_name: objName, loaded });
        if (loaded) break;
      }
      this.lastCarPath = objPath;
      return { bridge: 'electron-koffi', view, type: itemType, obj_path: objPath, obj_name: objName, loaded, attempts, car_cfg: carCfg, car_cfg_sub_dir: subDir, paint_ext: paintExt };
    },
    paint(data = {}) {
      const itemType = Number(data.itemType) || 0;
      const painted = funcs.viewerPaintItem ? Boolean(funcs.viewerPaintItem(
        0,
        itemType,
        Number(data.pattern) || 0,
        data.color1 || '000000',
        data.color2 || '000000',
        data.color3 || '000000',
        data.licenseColor || 'FFFFFF',
        Number(data.cust_id) || 0,
        data.allowCustomPaint !== false,
        Boolean(data.skipDecals),
        Number(data.number_font) || 0,
        Number(data.number_slant) || 0,
        data.number_color1 || '000000',
        data.number_color2 || '000000',
        data.number_color3 || '000000',
        data.car_number || '64',
        Number(data.sponsor1) || 0,
        Number(data.sponsor2) || 0,
        Number(data.club_id) || 0,
        Boolean(data.skipStamps),
        data.onCarName || '',
        Boolean(data.skipName),
      )) : false;
      let wheels = null;
      if (itemType === 0) {
        if (data.wheelColor && data.wheelId != null && funcs.viewerPaintWheelsCustom) {
          wheels = Boolean(funcs.viewerPaintWheelsCustom(0, data.wheelColor, Number(data.wheelId) || 0));
        } else if (funcs.viewerPaintWheelsDefault) {
          wheels = Boolean(funcs.viewerPaintWheelsDefault(0));
        }
      }
      return { bridge: 'electron-koffi', painted, wheels, item_type: itemType };
    },
    notify(data = {}) {
      const message = Number(data.message) || 0;
      if (message && funcs.onNotifyMsgRecv) {
        funcs.onNotifyMsgRecv(message);
        return { bridge: 'electron-koffi', forwarded: true, message };
      }
      return { bridge: 'electron-koffi', forwarded: false, message };
    },
    shutdown() {
      let deleted = null;
      if (this.viewCreated && funcs.viewerDeleteView) deleted = Boolean(funcs.viewerDeleteView(0));
      if (funcs.viewerSupportEnd) funcs.viewerSupportEnd();
      if (funcs.iRacingHostDeregister) funcs.iRacingHostDeregister();
      if (funcs.iRacingHostDeregisterDemo) funcs.iRacingHostDeregisterDemo();
      this.attachedHwnd = null;
      this.registrationMode = '';
      this.viewCreated = false;
      iracingNativeTargetWindow = null;
      closeIracingNativeHostWindow();
      return { bridge: 'electron-koffi', deleted, support_ended: true };
    },
  };
  debugLog(`[iRacingKoffi] loaded ${dllPath} via ${modulePath}`);
  return bridge;
}

function getIracingKoffiBridge() {
  if (!iracingKoffiBridge) iracingKoffiBridge = createIracingKoffiBridge();
  return iracingKoffiBridge;
}

function handleIracingKoffiBridgeCommand(command, data = {}) {
  const bridge = getIracingKoffiBridge();
  if (command === 'status') return bridge.status();
  if (command === 'attach') return bridge.attach(data);
  if (command === 'create') return bridge.create(data);
  if (command === 'resize') return bridge.resize(data);
  if (command === 'load') return bridge.load(data);
  if (command === 'paint') return bridge.paint(data);
  if (command === 'notify') return bridge.notify(data);
  if (command === 'shutdown') return bridge.shutdown(data);
  throw new Error(`Unknown iRacing native command: ${command}`);
}

async function sendIracingNativeBridgeCommandAuto(command, data = {}, timeoutMs = 12000) {
  try {
    return handleIracingKoffiBridgeCommand(command, data);
  } catch (err) {
    debugLog(`[iRacingKoffi] ${command} failed, falling back to Python helper: ${err.message}`);
    const result = await sendIracingNativeBridgeCommand(command, data, timeoutMs);
    if (result && typeof result === 'object' && !Array.isArray(result)) {
      return Object.assign({}, result, {
        preferred_bridge: 'electron-koffi',
        preferred_bridge_error: err.message,
        bridge_fallback: result.bridge || 'python-helper',
      });
    }
    return result;
  }
}

function rejectIracingPending(message) {
  for (const pending of iracingBridgePending.values()) {
    clearTimeout(pending.timer);
    pending.reject(new Error(message));
  }
  iracingBridgePending.clear();
}

function handleIracingBridgeLine(line) {
  if (!line) return;
  let payload;
  try {
    payload = JSON.parse(line);
  } catch (err) {
    debugLog(`[iRacingBridge] Non-JSON output: ${line.slice(0, 500)}`);
    return;
  }
  if (payload.kind === 'ready') {
    debugLog(`[iRacingBridge] Ready pid=${payload.pid || 'unknown'}`);
    return;
  }
  if (!payload.id || !iracingBridgePending.has(payload.id)) {
    debugLog(`[iRacingBridge] Event ${JSON.stringify(payload).slice(0, 1000)}`);
    return;
  }
  const pending = iracingBridgePending.get(payload.id);
  iracingBridgePending.delete(payload.id);
  clearTimeout(pending.timer);
  if (payload.success) pending.resolve(payload.result);
  else pending.reject(new Error(payload.error || 'iRacing native bridge command failed'));
}

function startIracingNativeBridgeProcess() {
  if (process.platform !== 'win32') {
    return Promise.reject(new Error('The iRacing native viewer bridge is Windows-only.'));
  }
  if (iracingBridgeProcess && iracingBridgeProcess.exitCode === null) {
    return Promise.resolve(true);
  }
  const scriptPath = getIracingNativeBridgeScriptPath();
  if (!fs.existsSync(scriptPath)) {
    return Promise.reject(new Error(`iRacing native bridge helper missing: ${scriptPath}`));
  }
  const bundledPython = getBundledPythonPath();
  const spawnExe = bundledPython || 'python';
  const spawnArgs = ['-u', scriptPath];
  debugLog(`[iRacingBridge] Starting ${spawnExe} ${spawnArgs.join(' ')}`);
  iracingBridgeProcess = spawn(spawnExe, spawnArgs, {
    cwd: getServerDir(),
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
    env: Object.assign({}, process.env, { PYTHONUNBUFFERED: '1' }),
  });
  iracingBridgeBuffer = '';
  iracingBridgeProcess.stdout.on('data', (data) => {
    iracingBridgeBuffer += data.toString('utf8');
    const lines = iracingBridgeBuffer.split(/\r?\n/);
    iracingBridgeBuffer = lines.pop() || '';
    for (const line of lines) handleIracingBridgeLine(line.trim());
  });
  iracingBridgeProcess.stderr.on('data', (data) => {
    const text = data.toString('utf8').trim();
    if (text) debugLog(`[iRacingBridge:stderr] ${text.slice(0, 2000)}`);
  });
  iracingBridgeProcess.on('error', (err) => {
    debugLog(`[iRacingBridge] process error: ${err.message}`);
    rejectIracingPending(`iRacing native bridge failed: ${err.message}`);
  });
  iracingBridgeProcess.on('exit', (code, signal) => {
    debugLog(`[iRacingBridge] exited code=${code} signal=${signal || ''}`);
    iracingBridgeProcess = null;
    rejectIracingPending('iRacing native bridge exited.');
  });
  return Promise.resolve(true);
}

async function sendIracingNativeBridgeCommand(command, data = {}, timeoutMs = 12000) {
  await startIracingNativeBridgeProcess();
  if (!iracingBridgeProcess || !iracingBridgeProcess.stdin || iracingBridgeProcess.exitCode !== null) {
    throw new Error('iRacing native bridge is not running.');
  }
  const id = `ir-${iracingBridgeSeq++}`;
  const message = JSON.stringify({ id, command, data }) + '\n';
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      iracingBridgePending.delete(id);
      reject(new Error(`iRacing native bridge timed out on ${command}.`));
    }, timeoutMs);
    iracingBridgePending.set(id, { resolve, reject, timer });
    try {
      iracingBridgeProcess.stdin.write(message, 'utf8');
    } catch (err) {
      clearTimeout(timer);
      iracingBridgePending.delete(id);
      reject(err);
    }
  });
}

function hookIracingNotifyMessages(win) {
  if (!win || win.isDestroyed() || iracingNotifyHookedWindows.has(win)) return;
  iracingNotifyHookedWindows.add(win);
  try {
    win.hookWindowMessage(75040, (wParam) => {
      let message = 0;
      try { message = wParam.readUInt32LE(0); } catch (_) {}
      if (message) {
        sendIracingNativeBridgeCommandAuto('notify', { message }, 2500).catch((err) => {
          debugLog(`[iRacingBridge] notify forward failed: ${err.message}`);
        });
      }
    });
  } catch (err) {
    debugLog(`[iRacingBridge] hookWindowMessage failed: ${err.message}`);
  }
}

function stopIracingNativeBridgeProcess(reason) {
  if (!iracingBridgeProcess) return;
  debugLog(`[iRacingBridge] stopping (${reason})`);
  try {
    if (iracingBridgeProcess.stdin && iracingBridgeProcess.exitCode === null) {
      iracingBridgeProcess.stdin.write(JSON.stringify({ id: `ir-${iracingBridgeSeq++}`, command: 'shutdown', data: {} }) + '\n');
    }
  } catch (_) {}
  try { iracingBridgeProcess.kill(); } catch (_) {}
  iracingBridgeProcess = null;
  rejectIracingPending('iRacing native bridge stopped.');
}

// ===== STABLE ORIGIN: production stays on 59876; dev may explicitly pin one port =====
function isPortFree(port) {
  return new Promise((resolve) => {
    const tester = net.createServer()
      .once('error', () => resolve(false))
      .once('listening', () => tester.close(() => resolve(true)))
      .listen(port, '127.0.0.1');
  });
}
async function pickServerPort(deps = {}) {
  const devPortRaw = Object.prototype.hasOwnProperty.call(deps, 'devPortRaw')
    ? deps.devPortRaw : process.env.SPB_DEV_PORT;
  let requestedPort = STABLE_SERVER_PORT;
  if (devPortRaw != null && String(devPortRaw).trim() !== '') {
    const devPort = Number.parseInt(String(devPortRaw), 10);
    if (!Number.isInteger(devPort) || devPort <= 0 || devPort >= 65536) {
      throw new Error(`SPB_DEV_PORT="${devPortRaw}" is invalid; expected a TCP port from 1 to 65535`);
    }
    requestedPort = devPort;
    debugLog(`[Server] Using intentional dev-pinned port ${requestedPort} (SPB_DEV_PORT)`);
  } else {
    debugLog(`[StableOrigin] Production origin pinned to http://127.0.0.1:${STABLE_SERVER_PORT}`);
  }
  const ensureAvailable = deps.ensureStableServerPortAvailable || ensureStableServerPortAvailable;
  await ensureAvailable(requestedPort, deps);
  return requestedPort;
}

function _isExpectedStartedChildIdentity(identity, port, childPid, serverDir) {
  return !!identity
    && identity.status === 'running'
    && identity.engine === SPB_BUILD_IDENTITY
    && Number(identity.port) === Number(port)
    && Number(identity.pid) === Number(childPid)
    && _sameStableOriginPath(identity.server_dir, serverDir);
}

// ===== START PYTHON SERVER (preserved bundled-Python preference) =====
function startServer(port) {
  return new Promise((resolve, reject) => {
    let startSettled = false;
    let pollInterval = null;
    const serverDir = getServerDir();
    const bundledPython = getBundledPythonPath();

    let spawnExe, spawnArgs, spawnCwd, spawnEnv;

    if (bundledPython) {
      debugLog(`[Server] Using bundled Python: ${bundledPython}`);
      spawnExe = bundledPython;
      spawnArgs = ['server_v5.py'];
      spawnCwd = serverDir;
      spawnEnv = Object.assign({}, process.env, {
        SHOKKER_PORT: String(port),
        SPB_USER_IMPORTS_DIR: path.join(APP_DATA_DIR, 'user_imports'),
        // Finish recipes still contain a handful of legacy hash()-derived
        // offsets. Python salts hash() per process unless this is fixed, which
        // made the same saved Spec Sculpt plan subtly change after an app
        // restart. Pin it before Python starts so named plans are reproducible.
        PYTHONHASHSEED: '0',
      });
    } else {
      debugLog('[Server] No bundled Python found, trying system Python');
      spawnExe = 'python';
      spawnArgs = ['server_v5.py'];
      spawnCwd = serverDir;
      spawnEnv = Object.assign({}, process.env, {
        SHOKKER_PORT: String(port),
        SPB_USER_IMPORTS_DIR: path.join(APP_DATA_DIR, 'user_imports'),
        PYTHONHASHSEED: '0',
      });
    }

    debugLog(`[Server] Server dir: ${serverDir}`);

    const child = spawn(spawnExe, spawnArgs, {
      env: spawnEnv,
      cwd: spawnCwd,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      detached: false
    });
    serverProcess = child;

    if (child.stdout) {
      child.stdout.on('data', (data) => {
        const lines = data.toString().split('\n').filter((l) => l.trim());
        for (const line of lines.slice(0, 5)) debugLog(`[Server:out] ${line.trim()}`);
      });
    }
    if (child.stderr) {
      child.stderr.on('data', (data) => {
        const lines = data.toString().split('\n').filter((l) => l.trim());
        for (const line of lines.slice(0, 10)) debugLog(`[Server:err] ${line.trim()}`);
      });
    }

    let childStartError = false;
    child.on('error', (err) => {
      childStartError = true;
      debugLog(`[Server] ERROR: Failed to start: ${err.message}`);
      if (!startSettled) {
        startSettled = true;
        reject(err);
      }
    });

    child.on('exit', (code, signal) => {
      const intentional = intentionalServerStops.has(child);
      debugLog(`[Server] Exited with code ${code}, signal ${signal || 'none'}${intentional ? ' (intentional)' : ''}`);
      // A killed predecessor can report exit after its replacement has spawned.
      // Never let that stale callback clear or restart the current child.
      if (serverProcess !== child) {
        debugLog('[Server] Ignoring stale child exit callback');
        if (!startSettled) {
          startSettled = true;
          reject(new Error('Server child was replaced before becoming ready'));
        }
        return;
      }
      if (pollInterval) clearInterval(pollInterval);
      serverProcess = null;
      serverReady = false;
      updateTrayServerStatus(false);
      if (!startSettled) {
        startSettled = true;
        reject(new Error(`Server exited before ready (code=${code}, signal=${signal || 'none'})`));
        return;
      }
      // [ULTRACODE 2026-08-22 M6] a crashed engine was NEVER restarted — the
      // buyer sat permanently offline until a full app restart. restartServer()
      // already has the taskkill + retry + cap-of-3 machinery; reuse it.
      if (!quitInProgress && !intentional && !childStartError) {
        debugLog('[Server] crash — scheduling auto-restart in 1s');
        setTimeout(() => {
          if (quitInProgress || serverProcess) {
            debugLog('[Server] auto-restart skipped; replacement child already exists or app is quitting');
            return;
          }
          restartServer().catch((e) => debugLog('[Server] auto-restart failed: ' + e.message));
        }, 1000);
      }
    });

    const startTime = Date.now();
    let healthPollInFlight = false;
    pollInterval = setInterval(async () => {
      if (startSettled || healthPollInFlight || serverProcess !== child) return;
      healthPollInFlight = true;
      try {
        const identity = await probeSpbServerIdentity(port, { timeoutMs: 600 });
        if (!_isExpectedStartedChildIdentity(identity, port, child.pid, serverDir)) return;
        if (startSettled || serverProcess !== child) return;
        clearInterval(pollInterval);
        console.log(`[Electron] Server identity ready on port ${port} (${Date.now() - startTime}ms)`);
        serverReady = true;
        updateTrayServerStatus(true);
        startSettled = true;
        resolve(port);
      } finally {
        healthPollInFlight = false;
      }
    }, 250);

    setTimeout(() => {
      if (startSettled) return;
      clearInterval(pollInterval);
      debugLog('[Server] TIMEOUT: exact child identity did not respond after 60 seconds');
      if (serverProcess === child && child.exitCode === null) {
        debugLog('[Server] Tracked child is still running but unverified — stopping it and failing closed');
        startSettled = true;
        intentionalServerStops.add(child);
        try {
          const { execFileSync } = require('child_process');
          execFileSync('taskkill.exe', ['/F', '/PID', String(child.pid), '/T'],
            { windowsHide: true, timeout: 5000, stdio: 'ignore' });
        } catch (_) {
          try { child.kill(); } catch (_) {}
        }
        if (serverProcess === child) serverProcess = null;
        reject(new Error(`Server child never published the expected SPB identity on stable port ${port}`));
      } else {
        debugLog('[Server] Process is DEAD — showing error dialog');
        dialog.showErrorBox('Shokker Paint Booth - Server Failed',
          'The Python engine failed to start.\n\n' +
          'Check the debug log at:\n' + LOG_FILE + '\n\n' +
          'Common causes:\n' +
          '• Antivirus blocking python.exe\n' +
          '• Missing Visual C++ Redistributable\n' +
          '• Port ' + port + ' in use by another app');
        startSettled = true;
        reject(new Error('Server process exited before responding'));
      }
    }, 60000);
  });
}

// ----- IMPROVEMENT #4: Retry helper around startServer -----
async function startServerWithRetry(port, attempts = 3) {
  let lastErr = null;
  for (let i = 1; i <= attempts; i++) {
    try {
      await startServer(port);
      return;
    } catch (e) {
      lastErr = e;
      debugLog(`[Server] Attempt ${i}/${attempts} failed: ${e.message}`);
      if (i < attempts) await new Promise((r) => setTimeout(r, 1500 * i));
    }
  }
  throw lastErr || new Error('Server failed to start after retries');
}

// ----- IMPROVEMENT #18: Watchdog — restart hung server (conservative; avoid killing server mid-render) -----
let _watchdogFailStreak = 0;
function startWatchdog() {
  if (process.env.SPB_DISABLE_SERVER_WATCHDOG === '1') {
    debugLog('[Watchdog] Disabled via SPB_DISABLE_SERVER_WATCHDOG=1');
    return;
  }
  if (watchdogTimer) clearInterval(watchdogTimer);
  _watchdogFailStreak = 0;
  watchdogTimer = setInterval(() => {
    if (!serverProcess) return; // already exited; the exit handler auto-restarts crashes [M6]
    const sock = new net.Socket();
    sock.setTimeout(8000);
    sock.once('connect', () => {
      sock.destroy();
      _watchdogFailStreak = 0;
    });
    const onFail = (reason) => {
      sock.destroy();
      if (!serverProcess) return;
      _watchdogFailStreak++;
      debugLog(`[Watchdog] Health check failed (${reason}); streak=${_watchdogFailStreak}`);
      if (_watchdogFailStreak >= 2) {
        debugLog('[Watchdog] Two consecutive failures — restarting server');
        _watchdogFailStreak = 0;
        restartServer();
      }
    };
    sock.once('timeout', () => onFail('timeout'));
    sock.once('error', () => onFail('error'));
    sock.connect(serverPort, '127.0.0.1');
  }, 120000);
}

async function restartServer() {
  if (serverRestartPromise) {
    debugLog('[Server] Restart already in flight; joining it');
    return serverRestartPromise;
  }
  if (serverRestartCount >= 3) {
    debugLog('[Watchdog] Restart cap reached (3); giving up');
    return;
  }
  serverRestartCount++;
  serverRestartPromise = (async () => {
    const childToStop = serverProcess;
    if (childToStop && childToStop.pid) {
      const { execFileSync } = require('child_process');
      intentionalServerStops.add(childToStop);
      try {
        execFileSync('taskkill.exe', ['/F', '/PID', String(childToStop.pid), '/T'],
          { windowsHide: true, timeout: 3000, stdio: 'ignore' });
      } catch (_) {
        try { childToStop.kill(); } catch (_) {}
      }
    }
    if (serverProcess === childToStop) serverProcess = null;
    serverReady = false;
    updateTrayServerStatus(false);
    if (childToStop) {
      if (!(await _waitForStablePortRelease(serverPort, 4000))) {
        throw new Error(`Tracked SPB server did not release stable port ${serverPort}; no replacement was started`);
      }
    } else {
      await ensureStableServerPortAvailable(serverPort);
    }
    await startServerWithRetry(serverPort, 2);
    // Confirmed-healthy restart: clear the lifetime cap so the watchdog can
    // recover from future, unrelated hangs instead of permanently giving up
    // after 3 restarts over the whole app session.
    serverRestartCount = 0;
    debugLog('[Watchdog] Server restarted');
    return true;
  })().catch((e) => {
    debugLog(`[Watchdog] Restart failed: ${e.message}`);
    try {
      dialog.showErrorBox('Shokker Paint Booth - Server Restart Blocked', e.message);
    } catch (_) {}
    return false;
  }).finally(() => {
    serverRestartPromise = null;
  });
  return serverRestartPromise;
}

// ===== IMPROVEMENT #1/22/23: Window state persistence + minimum size =====
function readWindowState() {
  try {
    if (!fs.existsSync(WINDOW_STATE_FILE)) return null;
    const state = JSON.parse(fs.readFileSync(WINDOW_STATE_FILE, 'utf8'));
    return state && typeof state === 'object' ? state : null;
  } catch (_) { return null; }
}
function writeWindowState(state) {
  try { fs.writeFileSync(WINDOW_STATE_FILE, JSON.stringify(state, null, 2), 'utf8'); } catch (_) {}
}
function clampToDisplay(state) {
  // ----- IMPROVEMENT #2: Multi-monitor — ensure window lands on a real display -----
  try {
    const displays = screen.getAllDisplays();
    const onScreen = displays.some((d) => {
      const b = d.workArea;
      return state.x >= b.x - 50 && state.x < b.x + b.width - 50 &&
             state.y >= b.y - 50 && state.y < b.y + b.height - 50;
    });
    if (!onScreen) {
      const primary = screen.getPrimaryDisplay().workArea;
      state.x = primary.x + Math.max(0, Math.floor((primary.width - state.width) / 2));
      state.y = primary.y + Math.max(0, Math.floor((primary.height - state.height) / 2));
    }
  } catch (_) {}
  return state;
}

// ===== IMPROVEMENT #24: Icon resolution with high-DPI fallback =====
function loadAppIcon() {
  const candidates = [
    path.join(__dirname, 'shokker-icon.ico'),
    path.join(__dirname, 'icon.ico'),
    path.join(__dirname, 'icon.png'),
    path.join(process.resourcesPath || '', 'shokker-icon.ico'),
  ];
  for (const p of candidates) {
    try {
      if (fs.existsSync(p)) {
        const img = nativeImage.createFromPath(p);
        if (!img.isEmpty()) return img;
      }
    } catch (_) {}
  }
  return undefined;
}

// ===== IMPROVEMENT #5: System tray with server status =====
function buildTrayMenu() {
  return Menu.buildFromTemplate([
    { label: serverReady ? 'Server: Running' : 'Server: Stopped', enabled: false },
    { type: 'separator' },
    { label: 'Show Window', click: () => {
      if (mainWindow) {
        if (mainWindow.isMinimized()) mainWindow.restore();
        mainWindow.show();
        mainWindow.focus();
      }
    } },
    { label: 'Restart Server', click: () => { restartServer(); } },
    { label: 'Open Logs Folder', click: () => { shell.openPath(LOG_DIR); } },
    { type: 'separator' },
    { label: 'About SPB', click: () => showAboutDialog() },
    { label: 'Quit', click: () => { quitInProgress = true; app.quit(); } },
  ]);
}
function setupTray() {
  try {
    const icon = loadAppIcon();
    tray = new Tray(icon || nativeImage.createEmpty());
    tray.setToolTip('Shokker Paint Booth');
    tray.setContextMenu(buildTrayMenu());
    tray.on('click', () => {
      if (!mainWindow) return;
      if (mainWindow.isVisible()) mainWindow.hide();
      else { mainWindow.show(); mainWindow.focus(); }
    });
  } catch (e) {
    debugLog(`[Tray] init failed: ${e.message}`);
  }
}
function updateTrayServerStatus(ready) {
  serverReady = !!ready;
  if (tray) {
    try {
      tray.setContextMenu(buildTrayMenu());
      tray.setToolTip(`Shokker Paint Booth — Server: ${ready ? 'Running' : 'Stopped'}`);
    } catch (_) {}
  }
  if (mainWindow && !mainWindow.isDestroyed()) {
    try { mainWindow.webContents.send('server-status', { ready }); } catch (_) {}
  }
}

// ===== IMPROVEMENT #12: Proper application menu =====
function buildAppMenu() {
  const isMac = process.platform === 'darwin';
  const template = [
    {
      label: 'File',
      submenu: [
        { label: 'Open Recent…', submenu: readRecentFiles().slice(0, 8).map((p) => ({
          label: path.basename(p),
          click: () => { if (mainWindow) mainWindow.webContents.send('menu-action', { action: 'open-file', path: p }); },
        })) },
        { type: 'separator' },
        { label: 'Quit', accelerator: isMac ? 'Cmd+Q' : 'Ctrl+Q', click: () => { quitInProgress = false; app.quit(); } },
      ],
    },
    { label: 'Edit', submenu: [
      { role: 'undo' }, { role: 'redo' }, { type: 'separator' },
      { role: 'cut' }, { role: 'copy' }, { role: 'paste' }, { role: 'selectAll' },
    ] },
    { label: 'View', submenu: [
      { label: 'Open Paint Lab', accelerator: 'Ctrl+Shift+V', click: () => openFinishViewerWindow() },
      { label: 'Open SPEC SCULPT', accelerator: 'Ctrl+Shift+S', click: () => openGuidedSpecSculpt() },
      { label: 'Open Original SPEC SCULPT', click: () => openSpecSculptWindow() },
      { label: 'Open Shokk Drop', accelerator: 'Ctrl+Shift+D', click: () => openShokkDropWindow() },
      // The original Spec Sculpt laboratory remains explicitly reachable;
      // Shokker Forge stays implemented but outside this beta's customer UI.
      { type: 'separator' },
      { label: 'Reload', accelerator: 'Ctrl+R', click: () => mainWindow && mainWindow.webContents.reload() },
      { label: 'Hard Reload', accelerator: 'Ctrl+Shift+R', click: async () => {
        if (!mainWindow) return;
        try { await mainWindow.webContents.session.clearCache(); } catch (_) {}
        mainWindow.webContents.reloadIgnoringCache();
      } },
      { label: 'Toggle Developer Tools', accelerator: 'F12', click: () => mainWindow && mainWindow.webContents.toggleDevTools() },
      { type: 'separator' },
      // ----- IMPROVEMENT #10: Disable zoom shortcuts (no-op handlers) -----
      { label: 'Actual Size', accelerator: 'Ctrl+0', click: () => { /* zoom disabled */ } },
      { label: 'Zoom In', accelerator: 'Ctrl+Plus', click: () => { /* zoom disabled */ } },
      { label: 'Zoom Out', accelerator: 'Ctrl+-', click: () => { /* zoom disabled */ } },
      { type: 'separator' },
      { role: 'togglefullscreen' },
    ] },
    { label: 'Window', submenu: [
      { role: 'minimize' }, { role: 'close' },
    ] },
    { label: 'Help', submenu: [
      { label: 'Open Logs Folder', click: () => shell.openPath(LOG_DIR) },
      { label: 'Open App Data Folder', click: () => shell.openPath(APP_DATA_DIR) },
      { label: 'Visit Shokker', click: () => shell.openExternal('https://shokkergroup.com') },
      { label: 'Releases', click: () => shell.openExternal('https://github.com/shokkergroup/ShokkerPaintBooth/releases') },
      { type: 'separator' },
      { label: 'About Shokker Paint Booth', click: () => showAboutDialog() },
    ] },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function showAboutDialog() {
  const win = mainWindow || BrowserWindow.getAllWindows()[0];
  dialog.showMessageBox(win, {
    type: 'info',
    title: 'About Shokker Paint Booth',
    message: `Shokker Paint Booth ${app.getVersion()}`,
    detail: [
      `Electron: ${process.versions.electron}`,
      `Chromium: ${process.versions.chrome}`,
      `Node: ${process.versions.node}`,
      `Platform: ${process.platform} ${os.release()}`,
      ``,
      `(c) ${new Date().getFullYear()} Shokker Group — All rights reserved.`,
      `Licensed via Payhip.`,
    ].join('\n'),
    buttons: ['Close', 'Copy Version'],
    defaultId: 0,
  }).then((res) => {
    if (res.response === 1) {
      try { electron.clipboard.writeText(`SPB ${app.getVersion()} (${process.versions.electron})`); } catch (_) {}
    }
  });
}

// 2026-06-07 browser-popping fix
// Distinguish the app's OWN windows (loopback server / local files) from REAL external
// links. The renderer opens its sub-tools and the "back to paint booth" view via
// window.open() to http://127.0.0.1:<port>/... — those must stay IN-APP, NOT get punted
// to the system browser. Only true external https?:// hosts (not 127.0.0.1 / localhost)
// should call shell.openExternal().
function isInternalAppUrl(rawUrl) {
  if (!rawUrl) return false;
  const u = String(rawUrl);
  // Local files and about:blank are always internal.
  if (/^file:/i.test(u) || /^about:blank$/i.test(u)) return true;
  if (!/^https?:\/\//i.test(u)) return false; // non-http(s) (mailto:, etc.) is "not internal"
  try {
    const host = new URL(u).hostname.toLowerCase();
    return host === '127.0.0.1' || host === 'localhost' || host === '::1' || host === '[::1]';
  } catch (_) {
    // Fallback: cheap substring check if URL parsing fails.
    return /\/\/(127\.0\.0\.1|localhost)(:|\/|$)/i.test(u);
  }
}

// 2026-06-07 browser-popping fix
// Map the renderer's named window.open() frameNames (2nd arg) to the EXISTING in-app
// window creators so those sub-tools open inside the app instead of the browser.
function routeNamedInternalWindow(frameName) {
  switch (frameName) {
    case 'shokkerSpecSculptLab':
      openSpecSculptWindow();
      return true;
    case 'shokkerShokkDrop':
      openShokkDropWindow();
      return true;
    case 'shokkerShokkForge':
      openShokkForgeWindow();
      return true;
    case 'shokkerFinishViewer':
      openFinishViewerWindow();
      return true;
    default:
      return false;
  }
}

// 2026-06-07 browser-popping fix
// Shared window-open policy for every BrowserWindow in the app:
//  - named internal sub-tools  -> open via their dedicated in-app creator, deny the popup
//  - other internal URLs (incl. the '_blank' back-to-paint-booth) -> allow an in-app window
//  - genuine external links     -> hand off to the system browser, deny the popup
function handleAppWindowOpen({ url: targetUrl, frameName }) {
  if (routeNamedInternalWindow(frameName)) {
    return { action: 'deny' };
  }
  if (isInternalAppUrl(targetUrl)) {
    return { action: 'allow' };
  }
  if (/^https?:\/\//i.test(targetUrl)) {
    shell.openExternal(targetUrl);
  }
  return { action: 'deny' };
}

function openFinishViewerWindow(options = {}) {
  if (!serverPort) {
    debugLog('[FinishViewer] Cannot open before the local server port is known');
    return false;
  }
  if (finishViewerWindow && !finishViewerWindow.isDestroyed()) {
    if (finishViewerWindow.isMinimized()) finishViewerWindow.restore();
    finishViewerWindow.show();
    finishViewerWindow.focus();
    return true;
  }

  const finish = String(options.finish || 'living_led_chase');
  const source = String(options.source || 'api');
  const params = new URLSearchParams({ source, finish });
  const url = `http://127.0.0.1:${serverPort}/finish-viewer.html?${params.toString()}`;
  finishViewerWindow = new BrowserWindow({
    width: 1500,
    height: 960,
    minWidth: 980,
    minHeight: 650,
    title: 'SHOKKER Paint Lab',
    backgroundColor: '#05080d',
    icon: loadAppIcon(),
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
      webSecurity: true,
      allowRunningInsecureContent: false,
      webgl: true,
      backgroundThrottling: false,
      spellcheck: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  // 2026-06-07 browser-popping fix: keep internal windows in-app, only punt true externals.
  finishViewerWindow.webContents.setWindowOpenHandler(handleAppWindowOpen);
  finishViewerWindow.webContents.on('will-navigate', (e, targetUrl) => {
    if (isPaintBoothRootNav(targetUrl)) { e.preventDefault(); focusMainPaintBooth(); return; }
    if (!targetUrl.startsWith(`http://127.0.0.1:${serverPort}`)) {
      e.preventDefault();
      if (/^https?:\/\//i.test(targetUrl)) shell.openExternal(targetUrl);
    }
  });
  finishViewerWindow.webContents.on('did-fail-load', (_e, errorCode, errorDesc, targetUrl) => {
    if (errorCode === -3) return;
    debugLog(`[FinishViewer] did-fail-load ${errorCode} ${errorDesc} for ${targetUrl}`);
  });
  finishViewerWindow.once('ready-to-show', () => {
    if (finishViewerWindow && !finishViewerWindow.isDestroyed()) finishViewerWindow.show();
  });
  finishViewerWindow.on('closed', () => {
    finishViewerWindow = null;
  });
  finishViewerWindow.loadURL(url);
  debugLog(`[FinishViewer] Opening ${url}`);
  return true;
}

// Back-navigation helpers (SPB 2026-06-08): sub-tool windows (Spec Sculpt / SHOKK DROP /
// Finish Viewer) must RETURN to the existing Paint Booth window — NOT navigate themselves
// into a second Paint Booth, and NOT 404 on /paint-booth-v2.html (which only serves at '/').
function isPaintBoothRootNav(targetUrl) {
  try {
    const u = new URL(targetUrl);
    const loopback = (u.hostname === '127.0.0.1' || u.hostname === 'localhost') && String(u.port) === String(serverPort);
    const root = u.pathname === '/' || u.pathname === '/index.html' || /paint-booth-v2\.html$/i.test(u.pathname);
    return loopback && root;
  } catch (_) { return false; }
}
function focusMainPaintBooth() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
  } else {
    try { createWindow(serverPort); } catch (_) {}
  }
}

// SPEC SCULPT COURSE CORRECTION 2026-07-18: the customer menu opens the
// focused all-looks workflow in the main booth. The full legacy laboratory
// below remains implemented as the intermediate advanced option.
function openGuidedSpecSculpt() {
  focusMainPaintBooth();
  if (!mainWindow || mainWindow.isDestroyed()) return false;
  mainWindow.webContents.executeJavaScript(
    'window.spbEasy && window.spbEasy.openSculpt ? window.spbEasy.openSculpt() : false'
  ).catch((err) => debugLog(`[SpecSculpt] Guided launch failed: ${err && err.message ? err.message : err}`));
  return true;
}

function openSpecSculptWindow() {
  if (!serverPort) {
    debugLog('[SpecSculpt] Cannot open before the local server port is known');
    return false;
  }
  if (specSculptWindow && !specSculptWindow.isDestroyed()) {
    if (specSculptWindow.isMinimized()) specSculptWindow.restore();
    specSculptWindow.show();
    specSculptWindow.focus();
    return true;
  }

  const url = `http://127.0.0.1:${serverPort}/spec-sculpt.html`;
  specSculptWindow = new BrowserWindow({
    width: 1500,
    height: 960,
    minWidth: 980,
    minHeight: 650,
    title: 'SHOKKER Spec Sculpt Lab',
    backgroundColor: '#05080d',
    icon: loadAppIcon(),
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
      webSecurity: true,
      allowRunningInsecureContent: false,
      webgl: true,
      backgroundThrottling: false,
      spellcheck: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  // 2026-06-07 browser-popping fix: keep internal windows in-app, only punt true externals.
  specSculptWindow.webContents.setWindowOpenHandler(handleAppWindowOpen);
  specSculptWindow.webContents.on('will-navigate', (e, targetUrl) => {
    if (isPaintBoothRootNav(targetUrl)) { e.preventDefault(); focusMainPaintBooth(); return; }
    if (!targetUrl.startsWith(`http://127.0.0.1:${serverPort}`)) {
      e.preventDefault();
      if (/^https?:\/\//i.test(targetUrl)) shell.openExternal(targetUrl);
    }
  });
  specSculptWindow.webContents.on('did-fail-load', (_e, errorCode, errorDesc, targetUrl) => {
    if (errorCode === -3) return;
    debugLog(`[SpecSculpt] did-fail-load ${errorCode} ${errorDesc} for ${targetUrl}`);
  });
  specSculptWindow.once('ready-to-show', () => {
    if (specSculptWindow && !specSculptWindow.isDestroyed()) specSculptWindow.show();
  });
  specSculptWindow.on('closed', () => {
    specSculptWindow = null;
  });
  specSculptWindow.loadURL(url);
  debugLog(`[SpecSculpt] Opening ${url}`);
  return true;
}

function openShokkDropWindow() {
  if (!serverPort) {
    debugLog('[ShokkDrop] Cannot open before the local server port is known');
    return false;
  }
  if (shokkDropWindow && !shokkDropWindow.isDestroyed()) {
    if (shokkDropWindow.isMinimized()) shokkDropWindow.restore();
    shokkDropWindow.show();
    shokkDropWindow.focus();
    return true;
  }

  const url = `http://127.0.0.1:${serverPort}/shokk-drop.html`;
  shokkDropWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 960,
    minHeight: 620,
    title: 'SHOKK DROP — Shokker Paint Booth',
    backgroundColor: '#07090d',
    icon: loadAppIcon(),
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
      webSecurity: true,
      allowRunningInsecureContent: false,
      webgl: true,
      backgroundThrottling: false,
      spellcheck: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  // 2026-06-07 browser-popping fix: keep internal windows in-app, only punt true externals.
  shokkDropWindow.webContents.setWindowOpenHandler(handleAppWindowOpen);
  shokkDropWindow.webContents.on('will-navigate', (e, targetUrl) => {
    if (isPaintBoothRootNav(targetUrl)) { e.preventDefault(); focusMainPaintBooth(); return; }
    if (!targetUrl.startsWith(`http://127.0.0.1:${serverPort}`)) {
      e.preventDefault();
      if (/^https?:\/\//i.test(targetUrl)) shell.openExternal(targetUrl);
    }
  });
  shokkDropWindow.once('ready-to-show', () => {
    if (shokkDropWindow && !shokkDropWindow.isDestroyed()) shokkDropWindow.show();
  });
  shokkDropWindow.on('closed', () => {
    shokkDropWindow = null;
  });
  shokkDropWindow.loadURL(url);
  debugLog(`[ShokkDrop] Opening ${url}`);
  return true;
}

function openShokkForgeWindow() {
  if (!serverPort) {
    debugLog('[ShokkForge] Cannot open before the local server port is known');
    return false;
  }
  if (shokkForgeWindow && !shokkForgeWindow.isDestroyed()) {
    if (shokkForgeWindow.isMinimized()) shokkForgeWindow.restore();
    shokkForgeWindow.show();
    shokkForgeWindow.focus();
    return true;
  }

  const url = `http://127.0.0.1:${serverPort}/forge-page.html`;
  shokkForgeWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 980,
    minHeight: 680,
    title: 'SHOKKER FORGE — Reference to Editable PSD',
    backgroundColor: '#070a0f',
    icon: loadAppIcon(),
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
      webSecurity: true,
      allowRunningInsecureContent: false,
      webgl: true,
      backgroundThrottling: false,
      spellcheck: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  });
  shokkForgeWindow.webContents.setWindowOpenHandler(handleAppWindowOpen);
  shokkForgeWindow.webContents.on('will-navigate', (event, targetUrl) => {
    if (isPaintBoothRootNav(targetUrl)) { event.preventDefault(); focusMainPaintBooth(); return; }
    if (!targetUrl.startsWith(`http://127.0.0.1:${serverPort}`)) {
      event.preventDefault();
      if (/^https?:\/\//i.test(targetUrl)) shell.openExternal(targetUrl);
    }
  });
  shokkForgeWindow.once('ready-to-show', () => {
    if (shokkForgeWindow && !shokkForgeWindow.isDestroyed()) shokkForgeWindow.show();
  });
  shokkForgeWindow.on('closed', () => { shokkForgeWindow = null; });
  shokkForgeWindow.loadURL(url);
  debugLog(`[ShokkForge] Opening ${url}`);
  return true;
}

// ===== CREATE WINDOW =====
function createWindow(port) {
  const saved = readWindowState() || {};
  const defaults = { width: 1600, height: 1000, x: undefined, y: undefined, isMaximized: false };
  const state = clampToDisplay(Object.assign({}, defaults, saved));

  mainWindow = new BrowserWindow({
    width: state.width,
    height: state.height,
    x: state.x,
    y: state.y,
    minWidth: 1100,
    minHeight: 720,
    title: 'Shokker Paint Booth',
    backgroundColor: '#111111',
    icon: loadAppIcon(),
    show: false, // ----- IMPROVEMENT #31: defer paint until ready-to-show -----
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false, // preload uses ipcRenderer
      webSecurity: true,
      allowRunningInsecureContent: false,
      experimentalFeatures: false,
      spellcheck: false,
      preload: path.join(__dirname, 'preload.js'),
      // ----- IMPROVEMENT #25: Pre-grant notification permission for our origin -----
      // (handled at the session level below)
    },
    autoHideMenuBar: true,
  });

  // ----- IMPROVEMENT #9: Content Security Policy -----
  // Allow loading from our own loopback server only.
  const cspValue = [
    "default-src 'self' http://127.0.0.1:* ws://127.0.0.1:*",
    "img-src 'self' data: blob: http://127.0.0.1:*",
    "style-src 'self' 'unsafe-inline' http://127.0.0.1:*",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' http://127.0.0.1:*",
    "connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:* https://payhip.com",
    "font-src 'self' data: http://127.0.0.1:*",
    "object-src 'none'",
    "base-uri 'self'",
  ].join('; ');
  mainWindow.webContents.session.webRequest.onHeadersReceived((details, callback) => {
    const headers = Object.assign({}, details.responseHeaders);
    headers['Content-Security-Policy'] = [cspValue];
    callback({ responseHeaders: headers });
  });

  // ----- IMPROVEMENT #25: pre-grant notification permission to loopback -----
  mainWindow.webContents.session.setPermissionRequestHandler((_wc, permission, cb, requestingOrigin) => {
    const origin = requestingOrigin || '';
    const trusted = origin.startsWith(`http://127.0.0.1:`);
    if (permission === 'notifications' && trusted) return cb(true);
    if (permission === 'clipboard-read' && trusted) return cb(true);
    if (permission === 'clipboard-sanitized-write' && trusted) return cb(true);
    return cb(false);
  });

  // ----- IMPROVEMENT #26: External links open in default browser -----
  // 2026-06-07 browser-popping fix: the renderer opens its sub-tools and the
  // "back to paint booth" view via window.open() to the app's OWN http://127.0.0.1
  // origin. The previous handler opened ANY http(s) url in the system browser, so
  // those internal windows popped the browser ("the browser pops up when I go back
  // to paint booth or click anything"). Route named internal sub-tools to their
  // in-app creators, keep other internal URLs in-app, and only openExternal for a
  // genuinely external host.
  mainWindow.webContents.setWindowOpenHandler(handleAppWindowOpen);
  mainWindow.webContents.on('will-navigate', (e, url) => {
    if (!url.startsWith(`http://127.0.0.1:`)) {
      e.preventDefault();
      if (/^https?:\/\//i.test(url)) shell.openExternal(url);
    }
  });

  // [2026-06-12 thumbnail-cache fix] BUILD 23 used to clearCache() on every
  // boot — that nuked the HTTP cache holding all picker swatch PNGs, so every
  // launch re-fetched ~2000 thumbnails ("always loading" bug). It's obsolete:
  // HTML and JS/CSS are served no-store/no-cache by the server (never stale),
  // and swatch URLs carry the engine-fingerprint ?v= token (auto-busted when
  // finishes actually change). Thumbnails now persist across launches, which
  // is exactly the behavior customer builds want. User-invoked Hard Reload
  // (Ctrl+Shift+R) still clears the cache for recovery.
  mainWindow.webContents.session.clearStorageData({
    storages: ['cachestorage', 'serviceworkers']
  }).catch(() => {});

  // ----- IMPROVEMENT #28: File drag-drop -----
  // The renderer handles dragover/drop, but we also pull paths through 'will-navigate'
  // when files are dropped onto the window itself.
  mainWindow.webContents.on('will-navigate', (e, url) => {
    if (url.startsWith('file:///')) e.preventDefault();
  });

  // ----- IMPROVEMENT #35: Fallback error page when renderer load fails -----
  mainWindow.webContents.on('did-fail-load', (_e, errorCode, errorDesc, validatedURL) => {
    debugLog(`[Renderer] did-fail-load ${errorCode} ${errorDesc} for ${validatedURL}`);
    if (errorCode === -3) return; // ABORTED — usually our own reload
    const html = `<!DOCTYPE html><html><body style="background:#0a0a0a;color:#e0e0e0;font-family:Segoe UI,sans-serif;padding:40px;text-align:center">
      <h1 style="color:#E87A20">Could not reach the engine</h1>
      <p>${errorDesc} (${errorCode})</p>
      <p style="color:#888">Tried: ${validatedURL}</p>
      <p style="margin-top:24px"><button onclick="location.reload()" style="padding:10px 20px;background:#E87A20;color:#fff;border:none;border-radius:6px;cursor:pointer">Retry</button></p>
      <p style="color:#666;margin-top:24px;font-size:12px">Logs: ${LOG_FILE.replace(/\\/g, '/')}</p>
    </body></html>`;
    mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html));
  });

  // ----- IMPROVEMENT #21: renderer process gone -----
  mainWindow.webContents.on('render-process-gone', (_e, details) => {
    debugLog(`[Renderer] render-process-gone reason=${details.reason} exitCode=${details.exitCode}`);
    if (details.reason !== 'clean-exit') {
      dialog.showErrorBox('Shokker Paint Booth', `The interface crashed (${details.reason}). The window will reload.`);
      try { mainWindow.reload(); } catch (_) {}
    }
  });

  const url = `http://127.0.0.1:${port}/`;
  console.log(`[Electron] Loading: ${url}`);
  mainWindow.loadURL(url);

  // ----- IMPROVEMENT #31: Show only when ready (no white flash) -----
  mainWindow.once('ready-to-show', () => {
    if (saved.isMaximized) mainWindow.maximize();
    mainWindow.show();
  });

  // ----- IMPROVEMENT #1/23: Persist window state on resize/move/maximize -----
  const saveBounds = () => {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    if (mainWindow.isMinimized()) return;
    const isMaximized = mainWindow.isMaximized();
    const bounds = isMaximized ? (saved && saved.width ? saved : mainWindow.getBounds()) : mainWindow.getBounds();
    writeWindowState({
      width: bounds.width, height: bounds.height,
      x: bounds.x, y: bounds.y, isMaximized,
    });
  };
  let saveTimer = null;
  const debouncedSave = () => {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(saveBounds, 500);
  };
  mainWindow.on('resize', debouncedSave);
  mainWindow.on('move', debouncedSave);
  mainWindow.on('maximize', saveBounds);
  mainWindow.on('unmaximize', saveBounds);
  mainWindow.on('close', saveBounds);

  // ----- IMPROVEMENT #14: Quit confirmation when unsaved -----
  mainWindow.on('close', (e) => {
    if (quitInProgress) return;
    if (!unsavedWork) return;
    e.preventDefault();
    const choice = dialog.showMessageBoxSync(mainWindow, {
      type: 'warning',
      buttons: ['Cancel', 'Discard & Quit'],
      defaultId: 0,
      cancelId: 0,
      title: 'Unsaved work',
      message: 'You have unsaved changes. Quit anyway?',
    });
    if (choice === 1) {
      unsavedWork = false;
      quitInProgress = true;
      mainWindow.close();
    }
  });

  // ----- IMPROVEMENT #2: Multi-monitor — react to display changes -----
  const onDisplayChange = () => {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    const bounds = mainWindow.getBounds();
    const fixed = clampToDisplay(bounds);
    if (fixed.x !== bounds.x || fixed.y !== bounds.y) {
      mainWindow.setBounds({ x: fixed.x, y: fixed.y, width: bounds.width, height: bounds.height });
      debugLog('[Display] Window re-positioned after display change');
    }
  };
  screen.on('display-removed', onDisplayChange);
  screen.on('display-metrics-changed', onDisplayChange);

  mainWindow.on('closed', () => {
    screen.off('display-removed', onDisplayChange);
    screen.off('display-metrics-changed', onDisplayChange);
    mainWindow = null;
  });
}

// ===== SPLASH / LOADING WINDOW =====
function showSplash(statusText) {
  if (splashWindow) {
    try { splashWindow.webContents.send('splash-status', statusText); } catch (_) {}
    return;
  }
  splashWindow = new BrowserWindow({
    width: 420, height: 260, frame: false, resizable: false,
    transparent: false, backgroundColor: '#0a0a0a',
    alwaysOnTop: false, skipTaskbar: false,
    icon: loadAppIcon(),
    webPreferences: { nodeIntegration: false, contextIsolation: true,
      preload: path.join(__dirname, 'license-preload.js') }
  });
  const splashHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:'Segoe UI',sans-serif;background:#0a0a0a;color:#e0e0e0;
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      height:100vh;padding:30px;-webkit-app-region:drag}
    h1{font-size:22px;font-weight:700;color:#E87A20;margin-bottom:10px;letter-spacing:1px}
    .status{font-size:14px;color:#999;margin-top:8px;text-align:center}
    .spinner{width:32px;height:32px;border:3px solid #333;border-top:3px solid #E87A20;
      border-radius:50%;animation:spin 1s linear infinite;margin:16px auto 8px}
    @keyframes spin{to{transform:rotate(360deg)}}
    </style></head><body>
    <h1>SHOKKER PAINT BOOTH</h1>
    <div class="spinner"></div>
    <div class="status" id="status">${statusText || 'Starting...'}</div>
    <script>
      // contextIsolation:true — use the preload-exposed bridge, not require().
      if (window.splashAPI && window.splashAPI.onStatus) {
        window.splashAPI.onStatus((msg) => {
          const el = document.getElementById('status');
          if (el) el.textContent = msg;
        });
      }
    </script>
    </body></html>`;
  splashWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(splashHtml));
  splashWindow.on('closed', () => { splashWindow = null; });
}

function closeSplash() {
  if (splashWindow) {
    try { splashWindow.close(); } catch (_) {}
    splashWindow = null;
  }
}

// ===== IMPROVEMENT #11: Custom protocol handler (shokker://) =====
try {
  if (process.defaultApp) {
    if (process.argv.length >= 2) app.setAsDefaultProtocolClient('shokker', process.execPath, [path.resolve(process.argv[1])]);
  } else {
    app.setAsDefaultProtocolClient('shokker');
  }
} catch (_) {}

function handleDeepLink(rawUrl) {
  if (!rawUrl || typeof rawUrl !== 'string') return;
  if (!rawUrl.toLowerCase().startsWith('shokker://')) return;
  debugLog(`[DeepLink] ${rawUrl}`);
  if (rawUrl.toLowerCase() === 'shokker://finish-viewer') {
    openFinishViewerWindow();
    return;
  }
  if (rawUrl.toLowerCase() === 'shokker://spec-sculpt') {
    openSpecSculptWindow();
    return;
  }
  let parsed;
  try { parsed = new URL(rawUrl); } catch (_) { return; }
  const isCommunityDrop = parsed.protocol === 'shokker:' && parsed.hostname === 'drop' &&
    parsed.pathname === '/install' && /^drp_[a-z0-9]{20,64}$/.test(parsed.searchParams.get('id') || '') &&
    (parsed.searchParams.get('version') || '1') === '1';
  if (!isCommunityDrop) return;
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show(); mainWindow.focus();
    if (rendererReadyForDeepLinks) {
      try { mainWindow.webContents.send('deep-link', rawUrl); } catch (_) { pendingDeepLinks.push(rawUrl); }
    } else if (!pendingDeepLinks.includes(rawUrl)) {
      pendingDeepLinks.push(rawUrl);
    }
  } else if (!pendingDeepLinks.includes(rawUrl)) {
    pendingDeepLinks.push(rawUrl);
  }
}

// ----- IMPROVEMENT #15: Honor second-instance: focus existing window -----
app.on('second-instance', (_event, argv) => {
  if (wantsFinishViewerLaunch(argv)) {
    openFinishViewerWindow();
  }
  if (wantsSpecSculptLaunch(argv)) {
    openSpecSculptWindow();
  }
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show(); mainWindow.focus();
  } else if (splashWindow && !splashWindow.isDestroyed()) {
    // App is still booting (no main window yet) — surface the in-progress launch so a stray
    // 2nd double-click focuses the splash instead of being a silent no-op (SPB 2026-06-08).
    try { if (splashWindow.isMinimized()) splashWindow.restore(); splashWindow.show(); splashWindow.focus(); } catch (_) {}
  }
  // Look for shokker:// or recent file path in the new instance's argv
  for (const a of argv) {
    if (typeof a === 'string' && a.toLowerCase().startsWith('shokker://')) handleDeepLink(a);
  }
});

// macOS open-url (kept for completeness; SPB ships Windows-only today)
app.on('open-url', (event, url) => { event.preventDefault(); handleDeepLink(url); });

// ===== APP LIFECYCLE =====
app.whenReady().then(async () => {
  try {
    debugLog('[Startup] app.whenReady fired');

    // SPB 2026-06-08: instant visible feedback. Show the splash BEFORE the license check —
    // that check can take up to ~20s on a slow/offline network (the verify wall-clock guard),
    // and on a cold unsigned ~2GB first launch this is the difference between the window
    // "doing nothing" and a visible spinner. Splash is NOT alwaysOnTop so the license dialog,
    // if shown, sits above it.
    try { app.setAppUserModelId('com.shokker.paintbooth.v6'); } catch (_) {}
    showSplash('Starting...');

    // ----- IMPROVEMENT #16: Auto-updater hooks (kept simple, deferred) -----
    // Wired further down once the window exists.

    const licensed = await checkLicenseAndActivate();
    debugLog(`[Startup] checkLicenseAndActivate returned: ${licensed}`);
    if (!(licensed === true || licensed === 'grace')) {
      debugLog('[Startup] No valid license - quitting');
      closeSplash();
      app.quit();
      return;
    }
    debugLog('[Startup] License validated - starting app');

    showSplash('Starting engine...');

    // Keep the production origin stable. The picker may reclaim one positively
    // verified orphaned SPB child; unknown listeners are never touched.
    showSplash('Checking stable engine port...');
    serverPort = await pickServerPort();
    debugLog(`[Startup] Starting server on port ${serverPort}...`);
    showSplash('Starting Python server...');
    await startServerWithRetry(serverPort, 3);
    debugLog('[Startup] Server started');
    showSplash('Loading interface...');

    // PyInstaller HTML workaround (preserved)
    try {
      const buildCheck = await new Promise((res, rej) => {
        http.get(`http://127.0.0.1:${serverPort}/build-check`, (resp) => {
          let data = '';
          resp.on('data', (chunk) => data += chunk);
          resp.on('end', () => { try { res(JSON.parse(data)); } catch (e) { rej(e); } });
        }).on('error', rej);
      });
      const srvDir = buildCheck.server_dir;
      debugLog(`[Startup] Server reports SERVER_DIR: ${srvDir}`);
      const htmlInSrvDir = path.join(srvDir, 'paint-booth-v2.html');
      if (!fs.existsSync(htmlInSrvDir)) {
        const srcHtml = path.join(getServerDir(), 'paint-booth-v2.html');
        if (fs.existsSync(srcHtml)) {
          fs.copyFileSync(srcHtml, htmlInSrvDir);
          debugLog(`[Startup] Copied HTML to server dir: ${htmlInSrvDir}`);
        } else {
          debugLog(`[Startup] WARNING: HTML not found at ${srcHtml}`);
        }
      } else {
        debugLog('[Startup] HTML already in server dir');
      }
    } catch (e) {
      debugLog(`[Startup] Build-check workaround failed: ${e.message}`);
    }

    debugLog('[Startup] Creating window...');
    buildAppMenu();
    setupTray();
    refreshJumpList();
    createWindow(serverPort);
    debugLog('[Startup] Window created - app should be visible');
    for (const arg of process.argv) {
      if (typeof arg === 'string' && arg.toLowerCase().startsWith('shokker://')) handleDeepLink(arg);
    }

    // Close splash once main window finishes loading
    mainWindow.webContents.once('did-finish-load', () => {
      closeSplash();
      debugLog('[Startup] Splash closed, main window loaded');
      try { mainWindow.webContents.send('server-status', { ready: serverReady, port: serverPort }); } catch (_) {}
      if (wantsFinishViewerLaunch()) openFinishViewerWindow();
      if (wantsSpecSculptLaunch()) openSpecSculptWindow();
    });
    setTimeout(closeSplash, 10000);

    // ----- IMPROVEMENT #30: Auto-reload on JS/HTML changes in dev mode -----
    if (!app.isPackaged) {
      try {
        const watchTargets = [path.join(getServerDir())];
        for (const target of watchTargets) {
          if (!fs.existsSync(target)) continue;
          fs.watch(target, { recursive: true }, (_evt, filename) => {
            if (!filename) return;
            if (/\.(html|css|js)$/i.test(filename)) {
              debugLog(`[Dev] File changed: ${filename} — reloading renderer`);
              if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.reload();
            }
          });
          debugLog(`[Dev] Watching ${target} for HTML/CSS/JS changes`);
        }
      } catch (e) { debugLog(`[Dev] Watch setup failed: ${e.message}`); }
    }

    // ----- IMPROVEMENT #18: Start the server watchdog -----
    startWatchdog();

    // ----- Power-save blocker (don't sleep mid-render) -----
    try { powerSaveBlockerId = powerSaveBlocker.start('prevent-app-suspension'); } catch (_) {}

    // ===== AUTO-UPDATER (preserved + a couple polish bits) =====
    setTimeout(() => {
      debugLog('[Updater] Checking for updates...');
      autoUpdater.logger = { info: (m) => debugLog(`[Updater] ${m}`), warn: (m) => debugLog(`[Updater] WARN: ${m}`), error: (m) => debugLog(`[Updater] ERR: ${m}`) };
      // USER chooses Download (not a forced background pull). The in-app
      // banner drives downloadUpdate() via the "start-update-download" IPC.
      autoUpdater.autoDownload = false;
      autoUpdater.autoInstallOnAppQuit = true;
      autoUpdater.allowPrerelease = true;

      autoUpdater.on('update-available', (info) => {
        debugLog(`[Updater] Update available: v${info.version}`);
        // Drive the in-app banner using the SAME payload shape as the
        // GitHub-poll banner path below. No blocking dialog — the user
        // chooses Download from the banner.
        if (mainWindow && !mainWindow.isDestroyed()) {
          try {
            mainWindow.webContents.send('update-banner', {
              latestVersion: info.version,
              releaseUrl: 'https://github.com/shokkergroup/ShokkerPaintBooth/releases',
              releaseNotes: info.releaseNotes || '',
              currentVersion: app.getVersion(),
            });
          } catch (e) {
            debugLog(`[Updater] banner send failed: ${e.message}`);
          }
        }
      });
      autoUpdater.on('update-not-available', () => debugLog('[Updater] No updates available - running latest version'));
      autoUpdater.on('download-progress', (p) => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          try {
            mainWindow.webContents.send('update-progress', { percent: Math.round((p && p.percent) || 0) });
          } catch (e) {
            debugLog(`[Updater] progress send failed: ${e.message}`);
          }
        }
      });
      autoUpdater.on('update-downloaded', (info) => {
        debugLog(`[Updater] Update downloaded: v${info.version}`);
        // Do NOT auto-quit. Tell the renderer it's ready; the user clicks Install.
        if (mainWindow && !mainWindow.isDestroyed()) {
          try {
            mainWindow.webContents.send('update-ready', { version: info.version });
          } catch (e) {
            debugLog(`[Updater] ready send failed: ${e.message}`);
          }
        }
      });
      autoUpdater.on('error', (err) => debugLog(`[Updater] Error: ${err.message}`));
      autoUpdater.checkForUpdates().catch((err) => debugLog(`[Updater] Check failed: ${err.message}`));
    }, 5000);

    // ===== IN-APP UPDATE BANNER (GitHub Releases poll) =====
    // Runs IN ADDITION to electron-updater. Because builds are unsigned,
    // electron-updater silently fails the install step; this banner gives
    // users a manual "Download Update" link via shell.openExternal.
    // Fires ~3s after window load — not blocking startup.
    setTimeout(() => {
      try {
        const currentVersion = app.getVersion();
        debugLog(`[UpdateBanner] Checking GitHub for updates (current v${currentVersion})`);
        updateCheck.checkForUpdate(currentVersion).then((result) => {
          debugLog(`[UpdateBanner] result: available=${result.updateAvailable} latest=${result.latestVersion || 'n/a'} reason=${result.reason || ''}`);
          if (result.updateAvailable && mainWindow && !mainWindow.isDestroyed()) {
            try {
              mainWindow.webContents.send('update-banner', {
                latestVersion: result.latestVersion,
                releaseUrl: result.releaseUrl,
                releaseNotes: result.releaseNotes,
                currentVersion,
              });
            } catch (e) {
              debugLog(`[UpdateBanner] send failed: ${e.message}`);
            }
          }
        }).catch((err) => {
          debugLog(`[UpdateBanner] check threw (should not happen): ${err.message}`);
        });
      } catch (e) {
        debugLog(`[UpdateBanner] setup failed: ${e.message}`);
      }
    }, 3000);

  } catch (err) {
    debugLog(`[Startup] CATCH ERROR: ${err.message}`);
    dialog.showErrorBox(
      'Shokker Paint Booth - Startup Error',
      `Failed to start the Shokker server.\n\n${err.message}\n\nPlease report this to Ricky.`
    );
    app.quit();
  }
});

// ===== IMPROVEMENT #37: Graceful shutdown sequence =====
function gracefulShutdown(reason) {
  debugLog(`[Shutdown] gracefulShutdown(${reason})`);
  try { if (watchdogTimer) clearInterval(watchdogTimer); } catch (_) {}
  try { if (powerSaveBlockerId !== null) powerSaveBlocker.stop(powerSaveBlockerId); } catch (_) {}
  try {
    if (iracingKoffiBridge) iracingKoffiBridge.shutdown();
  } catch (_) {}
  closeIracingNativeHostWindow();
  stopIracingNativeBridgeProcess(reason);
  const { execFileSync } = require('child_process');
  if (serverProcess && serverProcess.pid) {
    console.log(`[Electron] Killing server PID ${serverProcess.pid}...`);
    try {
      execFileSync('taskkill.exe', ['/F', '/PID', String(serverProcess.pid), '/T'],
        { windowsHide: true, timeout: 5000, stdio: 'ignore' });
    } catch (e) {
      console.log('[Electron] taskkill failed:', e.message);
      try { serverProcess.kill(); } catch (_) {}
    }
  }
  // Never sweep image names or port owners during shutdown. A future launch
  // health-checks any residue and reclaims it only if it is a verified orphan.
  serverProcess = null;
}

app.on('window-all-closed', () => {
  if (!mainWindow && BrowserWindow.getAllWindows().length === 0 && !serverReady) {
    debugLog('[Lifecycle] window-all-closed fired but no mainWindow yet - ignoring (license flow)');
    return;
  }
  debugLog('[Lifecycle] window-all-closed - shutting down');
  gracefulShutdown('window-all-closed');
  app.quit();
});

app.on('before-quit', () => {
  quitInProgress = true;
  gracefulShutdown('before-quit');
});

// Defense in depth: ensure children die if Electron itself dies hard.
process.on('exit', () => { try { gracefulShutdown('process-exit'); } catch (_) {} });
process.on('uncaughtException', (err) => {
  debugLog(`[Process] uncaughtException: ${err && err.stack || err}`);
});
process.on('unhandledRejection', (reason) => {
  debugLog(`[Process] unhandledRejection: ${reason && reason.stack || reason}`);
});
